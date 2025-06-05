#!/usr/bin/env python 
from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Optional, Iterable, Dict, Any, Sequence, Callable
from pathlib import Path
from functools import wraps
from collections import Counter

pd.set_option('future.no_silent_downcasting', True)

def _rename_columns(sheets) -> pd.DataFrame:
    """
    Rename specific columns in the DataFrame for consistency.
    """
    column_mapping = {
        "Name": "userName",
        "roomID": "roomId",
        "name": "roomName",
        "userIdAnonym": "userId",
        "at": "blockedFrom",
        "blockedByIdAnonym": "userId",
    }

    for sheet_name, data in sheets.items():
        # Strip trailing whitespaces from all column names
        data.columns = data.columns.str.strip()
        # Replace all occurrences of "null" or any string that consists only of whitespaces with NaN
        # Use a regex sind there are many trailing whitespaces and so on
        sheets[sheet_name] = data.replace(r'^\s*(null|\s*)\s*$', np.nan, regex=True).infer_objects(copy=False)
        sheets[sheet_name] = sheets[sheet_name].rename(columns=column_mapping)
    
    return sheets

def get_desk_room_mapping(sheets: pd.DataFrame) -> pd.DataFrame:
    """Creates a mapping between desks and rooms"""
    desk_room_mapping = sheets["fixedBooking"][["id", "deskNumber", "roomId"]].rename(columns={"id": "deskId"}).astype(int)
    desk_room_mapping = pd.merge(desk_room_mapping, sheets["room"], how="left", left_on="roomId", right_on="id").drop(columns="id")
    # Room in the database looks like Raum "Dechbetten" but we just wanna stick with Dechbetten (way easier to handle later)
    desk_room_mapping['roomName'] = desk_room_mapping['roomName'].str.extract(r'"([^"]+)"', expand=False)

    return desk_room_mapping    

def get_sheets(path: Path = (Path(__file__).resolve().parent.parent / 'data' / 'OpTisch_anonymisiert.xlsx')):
    # Load all sheets from the Excel file into a dictionary of DataFrames
    sheets = pd.read_excel(path, sheet_name=None)
    sheets = _rename_columns(sheets)

    # there is a missing value in the database therefore fill it and convert the columns to ints afterwards (from float due to the NaN value)
    sheets["fixedBooking"].loc[sheets["fixedBooking"]["id"] == 5, "deskNumber"] = 1
    sheets["fixedBooking"]["deskNumber"] = sheets["fixedBooking"]["deskNumber"].astype(int)
    # userIds are off by one in the database therefore incremente it
    sheets["variableBooking"]["userId"] += 1

    return sheets

def join_fixed_bookings(sheets, desk_room_mapping):
    data_fixed = pd.merge(sheets["fixedBooking"], sheets["user"], how="left", left_on="userId", right_on="ID").drop(columns=["ID"])
    data_fixed = pd.merge(data_fixed, desk_room_mapping[['roomName', 'deskId']], left_on='id', right_on="deskId", how='left')
    data_fixed["variableBooking"] = 0 # Indicate fixed bookings
    # According to Mr. Fraunhofer, these are leftover entries from old bookings. Therefore we just drop them.
    data_fixed = data_fixed.dropna(subset=['userId', 'blockedUntil'], how='all')
    data_fixed.loc[data_fixed['blockedUntil'].isna(), 'blockedUntil'] = 'unlimited'

    return data_fixed

def join_variable_bookings(sheets, desk_room_mapping):
    data_variable = pd.merge(sheets["variableBooking"], sheets["user"], how="left", left_on="userId", right_on="ID").drop(columns=["ID"])
    data_variable = pd.merge(data_variable, desk_room_mapping, on='deskId', how='left')
    # Since variable bookings are just for one day we fill the blockeduntil column with the same value to make comparions later on easier
    data_variable["blockedUntil"] = data_variable["blockedFrom"]
    data_variable["variableBooking"] = 1 # Indicate variable bookings

    return data_variable

def map_usernames(data):
    # adds the id to the duplicates names to be sure that it can be used as index (unique)
    dup = data["userName"].duplicated(keep=False)
    data.loc[dup, "userName"] = data["userName"] + "_" + data["ID"].astype(str)
    return dict(zip(data["ID"], data["userName"]))

def create_dataset(path: Path = (Path(__file__).resolve().parent.parent / 'data' / 'OpTisch_anonymisiert.xlsx')) -> Dataset:
    """This Function denormalizes the excel file to make it easier to handle.

    Returns:
        Dataset: A denormalized dataset
    """
    sheets = get_sheets(path)
    desk_room_mapping = get_desk_room_mapping(sheets)
    Dataset.set_desk_room_mapping(desk_room_mapping)
    data_fixed = join_fixed_bookings(sheets, desk_room_mapping)
    data_variable = join_variable_bookings(sheets, desk_room_mapping)
    data = pd.concat([data_fixed, data_variable], axis=0).rename(columns={"id": "bookingId"}).reset_index(drop=True)
    # its a float before since there are some NaN values in it
    data["userId"] = data["userId"].astype(int)
    userid_username_mapping = map_usernames(sheets["user"])
    Dataset.set_userid_username_mapping(userid_username_mapping)

    return Dataset(data)

class Dataset(pd.DataFrame):
    # both things make it easier/more efficent to map ids to names in case of sliced datasets 
    _desk_room_mapping: pd.DataFrame
    _userid_username_mapping: dict
    _date_format_mapping: dict[str, str] = {
        "year": "Y",
        "month": "M",
        "week": "W",
        "day": "D"
    }

    def return_if_empty(return_value: Optional[Any] = "self"):
        def decorator(method: Callable[[Any, Any], Any]) -> Callable[[Any, Any], Any]:
            @wraps(method)
            def wrapper(self: Dataset, *args, **kwargs) -> Any:
                if self.empty:
                    return self if return_value == "self" else return_value
                return method(self, *args, **kwargs)
            return wrapper
        return decorator

    def __init__(self, data = None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

    @classmethod
    def set_desk_room_mapping(cls, desk_room_mapping: pd.DataFrame):
        cls._desk_room_mapping = desk_room_mapping

    @classmethod
    def set_userid_username_mapping(cls, userid_username_mapping: dict):
        cls._userid_username_mapping = userid_username_mapping

    def drop_fixed(self):
        return self[self["variableBooking"] == 1]

    def get_timeframe(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, show_available: bool = False, only_active: bool = False) -> Dataset:
        """Filters desk data based on time constraints and availability status.
        
        Filters the DataFrame to show desks that are either blocked or available within
        the specified time period, with options to show only currently active blocks.

        Args:
            start_date: Minimum date for filtering blocked periods.
                Only blocks starting on or after this date will be included.
                If None, its unlimited.
            end_date: Maximum date for filtering blocked periods.
                Only blocks ending on or before this date will be included.
                If None, its unlimited.
            show_available: If True, returns available desks instead of blocked ones.
                Available desks are those NOT matching the other filter criteria.
            only_active: If True, returns only blocks that are currently active

        Returns:
            Filtered DataFrame containing only the rows that match the criteria."""
        
        mask = pd.Series(True, index=self.index)

        def exchange_dates_with_intersection(blocked_from, blocked_until):
            # this blocks handles the fixed bookings and takes the intersection between start and end
            # blockFrom and blockedUntil is longer
            is_fixed = self["variableBooking"] == 0
            blocked_from[is_fixed] = blocked_from[is_fixed].combine(start_date, func=max)
            blocked_until[is_fixed] = blocked_until[is_fixed].combine(end_date, func=min)
            self.loc[:, 'blockedFrom'] = blocked_from  # FIXME: CHANGED
            self.loc[:, 'blockedUntil'] = blocked_until.copy().replace(datetime.date(pd.Timestamp.max), 'unlimited')
        
        if start_date or end_date or only_active:
            blocked_from = pd.to_datetime(self['blockedFrom'])
            # treat unlimited endtime as a very high number to make the comparison easier later
            blocked_until = pd.to_datetime(self['blockedUntil'].copy().replace('unlimited',  datetime.date(pd.Timestamp.max)))

            exchange_dates_with_intersection(blocked_from, blocked_until)

            # drop all where blocked become bigger than until
            mask &= (blocked_from <= blocked_until)
            
            if start_date:
                mask &= (blocked_from >= start_date)
            if end_date:
                mask &= (blocked_until <= end_date)
            
            if only_active:
                mask &= (blocked_from >= datetime.today()) & (datetime.today() <= blocked_until)
            
        if show_available:
            mask = (~mask)

        return self[mask]

    @return_if_empty("self")
    def get_days(self, weekdays: list[str], only_active: bool = False) -> Dataset:
        """Filters desk data based on specific weekdays when desks are blocked.
        
        Args:
            weekdays: List of weekday names to filter (e.g., ['monday', 'tuesday']).
                Valid values: 'monday', 'tuesday', 'wednesday', 'thursday',
                'friday', 'saturday', 'sunday' (case-sensitive)
            only_active: If True, returns only blocks that are currently active
                (today is between blockedFrom and blockedUntil).
                
        Returns:
            Filtered Dataset containing only blocks starting on specified weekdays.
            
        Raises:
            KeyError: If invalid weekday names are provided in weekdays list.
            
        Example:
            >>> get_days(df, ['monday', 'friday'], only_active=True)
            # Returns desks blocked on Mondays or Fridays that are currently active
        """
        weekdays_map = {
            'monday': 0,
            'tuesday': 1,
            'wednesday': 2,
            'thursday': 3,
            'friday': 4,
            'saturday': 5,
            'sunday': 6
        }

        weekday_numbers = [weekdays_map[day] for day in weekdays]

        blocked_from = pd.to_datetime(self['blockedFrom'])
        blocked_until = pd.to_datetime(self['blockedUntil'].copy().replace('unlimited', datetime.date(pd.Timestamp.max)))

        mask = blocked_from.dt.weekday.isin(weekday_numbers)

        if only_active:
            mask &= (blocked_from >= datetime.today()) & (datetime.today() <= blocked_until)

        return self[mask]

    @property
    def _constructor(self):
        return Dataset

    @return_if_empty("self")
    def get_users(self, user_names: str | Sequence[str] = [], user_ids: int | Sequence[int] = [])  -> Dataset:
        """Filters desk data based on user names or IDs.
        
        Args:
            user_names: List of user names to filter (OR condition).
            user_ids: List of user IDs to filter (OR condition).
                
        Returns:
            Filtered Dataset where either user_name or user_id matches.
            
        Example:
            >>> get_users(df, user_names=['Hiro Tanaka', 'Emma Brown'], user_ids=[5, 3])
            # Returns desks booked by either Hiro Tanaka, Emma Brown, or users with ID 5 or 3
        """
        user_names = [user_names] if isinstance(user_names, str) else user_names
        user_ids = [user_ids] if isinstance(user_ids, int) else user_ids

        return self[self['userId'].isin(user_ids) | self['userName'].isin(user_names)]

    @return_if_empty("self")
    def get_rooms(self, room_names: list[str] = [], room_ids: list[int] = []) -> Dataset:
        """Filters desk data based on room names or IDs.
        
        Args:
            room_names: List of room names to filter (OR condition).
            room_ids: List of room IDs to filter (OR condition).
                
        Returns:
            Filtered DataFrame where either room_name or room_id matches.
            
        Example:
            >>> get_rooms(df, room_names=['Stadtamhof'], room_ids=[50])
            # Returns desks in either 'Stadtamhof' or room with ID 50
        """
        return self[self['roomName'].isin(room_names) | self['roomId'].isin(room_ids)]

    @return_if_empty("self")
    def get_desks(self, desk_ids: list[int] = []) -> Dataset:
        """Filters desk data based on desk IDs.
        
        Args:
            data: DataFrame containing desk information.
            desk_ids: List of desk IDs to filter.
                
        Returns:
            Filtered DataFrame containing only the specified desks.
            
        Example:
            >>> get_desks(df, desk_ids=[3, 12])
            # Returns only desks with IDs 3 and 12
        """
        return self[self["deskId"].isin(desk_ids)]

    @return_if_empty("self")
    def sort_bookings(self, by: str | Sequence[str], ascending: bool = False, **kwargs):
        return self.sort_values(by=by, ascending=ascending, **kwargs)

    @return_if_empty("self")
    def group_bookings(self, 
                       by: str | Iterable[str], 
                       aggregation: Optional[dict[str, tuple[str, Any]]] = None, 
                       aggregation_treshhold: int = 0,
                       agg_col_name: Optional[str] = None) -> Dataset:

        grouped_data = self.groupby(by)
        if aggregation:
            grouped_data = grouped_data.agg(**aggregation)
            grouped_data = grouped_data[grouped_data[agg_col_name] >= aggregation_treshhold]
        return Dataset(grouped_data)

    @return_if_empty("self")
    def mean_bookings(self):
        self = self.mean().to_frame().T
        self.index = ["total_mean"]
        return self

    @return_if_empty("self")
    def expand_time_intervals(self, granularity, start_col="blockedFrom", end_col="blockedUntil", column_name: Optional[str] = None):
        def get_period(row):
            dates = pd.date_range(row[start_col], row[end_col], freq='B').to_period(self._date_format_mapping[granularity])
            return dates

        column_name = column_name if column_name else f"expanded_{granularity}"
        self[column_name] = self.replace("unlimited", datetime.today()).apply(get_period, axis=1)

        return self

    @return_if_empty("self")
    def expand_time_intervals_desks(self, granularity, start_col="blockedFrom", end_col="blockedUntil", column_name: Optional[str] = None) -> Dataset:
        if not self.empty:
            column_name = column_name if column_name else f"expanded_desks_{granularity}"
            self = self.expand_time_intervals(granularity, start_col, end_col, column_name=column_name)
            self = self.apply(lambda row: [row["deskId"]] * len(row[column_name]), axis=1)
        return self

    @return_if_empty("self")
    def expand_time_intervals_counts(self, granularity, start_col="blockedFrom", end_col="blockedUntil", column_name: Optional[str] = None) -> Dataset:
        if not self.empty:
            column_name = column_name if column_name else f"expanded_counts_{granularity}"
            self = self.expand_time_intervals(granularity, start_col, end_col, column_name=column_name)
            self[column_name] = self[column_name].map(Counter)
        return self

    @return_if_empty("self")
    def weekday_counter(self, weekdays: list[str], column_counter: str="weekday_count", column_desks: str="expanded_desks_day"):
        """
        Counts the occurrence of a weekday within the booking period. Example: Booking from Monday to Friday 
        -> Returns a dataframe that has each weekday as a column (if the weekdays were specified) with their number.
        In the example, 1 for each weekday.
        """
        
        def weekdays_count(periods):
            weekdays = [p.weekday for p in periods]
            counter = Counter(weekdays)    
            return {day: counter.get(day, 0) for day in weekdays}
        self[column_counter] = self[column_desks].apply(weekdays_count)  
        
        weekday_df = pd.json_normalize(self['weekday_count']).fillna(0).astype(int)
        weekday_df.columns = weekdays
        weekday_df.index = self.index
        return weekday_df

    @return_if_empty("self")
    def expand_time_interval_desk_counter(self, weekdays: list[str]=["monday", "tuesday", "wednesday", "thursday", "friday"]):
        """
        Function creates a dataframe which shows the username,
        when he booked which tables, as well as the number of table bookings with the number on which weekday they were booked
        
        Dataframe with columns [userId, userName, deskId, num_desk_bookings, Monday, Tuesday,..., Friday, percentage_of_user].
        For each user, all booked tables, their total frequency,
        and how often they were booked on which day of the week can be viewed.
        Args:
            weekdays: Weekdays to be considered for statistics
        Returns:
            pd.Dataframe
        """
        desks = self.expand_time_intervals_desks("day")
        weekday_df = self.weekday_counter(weekdays)  

        df = pd.concat([self, weekday_df], axis=1)
        df["num_desk_bookings"] = desks.apply(len)

        aggregation = {"num_desk_bookings": ("num_desk_bookings", "sum"),}
        aggregation.update({col: (col, "sum") for col in weekdays})
        df = df.group_bookings(by=["userId", "userName", "deskId"],
                            aggregation=aggregation,
                            agg_col_name="num_desk_bookings")

        df[weekdays] = df[weekdays].astype(float) 
        # delete the previously added column
        self.drop(columns=["weekday_count"], inplace=True)

        df.loc[:, weekdays] = (df.loc[:, weekdays].div(df["num_desk_bookings"], axis=0)* 100).round(2)
        df["percentage_of_user"] = (df['num_desk_bookings'] / df.groupby(level='userId')['num_desk_bookings'].transform('sum') * 100).round(2)

        return df

    
    @return_if_empty("self")
    def get_double_bookings(self, start_col="blockedFrom", end_col="blockedUntil") -> Dataset:
        def has_overlapping_bookings(group):
            """All bookings for a user are processed. "Unlimited" is converted to a date far in the future. 
            The rows are then sorted chronologically, with early bookings appearing first."""
            group = group.replace('unlimited', datetime.date(pd.Timestamp.max)).sort_values(start_col)
            blocked_from = pd.to_datetime(group[start_col])
            blocked_until = pd.to_datetime(group[end_col])
            overlaps = blocked_until.shift() > blocked_from
            # return both entires not just the overlapsing on (second on)
            return group[overlaps | overlaps.shift(-1, fill_value=False)].replace(datetime.date(pd.Timestamp.max), 'unlimited')   

        double_bookings = self.groupby('userId', group_keys=False).apply(has_overlapping_bookings)

        return double_bookings

    @return_if_empty("self")
    def drop_double_bookings(self, start_col="blockedFrom", end_col="blockedUntil"):
        double_bookings = self.get_double_bookings(start_col=start_col, end_col=end_col)
        return self.drop(index=double_bookings.index)

    @return_if_empty(return_value=0)
    def get_desks_count(self):
        """
        Returns the total number of unique desks in the dataset.

        Returns:
            int: Number of unique desk identifiers across all rooms.
        """

        return len(self["deskId"].unique())

    @return_if_empty(return_value={})
    def get_desks_per_room_count(self) -> dict[str, int]:
        """
        Returns the number of unique desks per room.

        Args:
            data: DataFrame with at least 'room_name' and 'desk_id' columns.

        Returns:
            Dictionary mapping room_name to number of unique desks.
        """

        return self.groupby("roomName")["deskId"].nunique()

    @return_if_empty(return_value=0)
    def get_employees_count(self) -> int:
        """
        Returns the number of unique employees (users) in the dataset.

        Args:
            data: DataFrame containing booking information with a 'userId' column.

        Returns:
            int: Number of unique user IDs (i.e., distinct employees).
        """

        return self["userId"].nunique()

if __name__ == "__main__":
    data = create_dataset()
    #dataset.to_csv("OpTisch.csv", index=False)  # Save dataset to CSV without index
    # Some manipulation to showcase the usage
    # Manipulation functions are staticmethods to make it more generic usable
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 5, 21)
    data_timeframe = data.get_timeframe(start_date=start_date, end_date=end_date, show_available=False)    
    data_days = data_timeframe.get_days(weekdays=["monday", "wednesday"])
    data_rooms = data_days.get_rooms(room_names=["Dechbetten", "Westenviertel"], room_ids=[2, 9, 5])
    data_desks = data_rooms.get_desks(desk_ids=[5, 9, 12])
