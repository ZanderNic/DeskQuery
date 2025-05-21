#!/usr/bin/env python 
from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Literal
from pathlib import Path
#from deskquery.functions.core.utilization import expand_fixed_bookings

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

def create_dataset(path: Path= (Path(__file__).resolve().parent.parent / 'data' / 'OpTisch_anonymisiert.xlsx')) -> Dataset:
    """This Function denormalizes the excel file to make it easier to handle.

    Returns:
        Dataset: A denormalized dataset
    """
    sheets = get_sheets(path)
    desk_room_mapping = get_desk_room_mapping(sheets)
    data_fixed = join_fixed_bookings(sheets, desk_room_mapping)
    data_variable = join_variable_bookings(sheets, desk_room_mapping)

    data = pd.concat([data_fixed, data_variable], axis=0).rename(columns={"id": "bookingId"})

    return Dataset(data)


class Dataset:
    def __init__(self, data):
        self.data = data
    
    def __str__(self):
        return str(self.data)
    
    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value

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
        
        mask = pd.Series(True, index=self.data.index)
        
        if start_date or end_date or only_active:
            blocked_from = pd.to_datetime(self.data['blockedFrom'])
            # tread unlimited endtime as a very high number to make the comparison easier later
            blocked_until = pd.to_datetime(self.data['blockedUntil'].copy().replace('unlimited', datetime(2099, 12, 31)))

            if start_date:
                mask &= (blocked_from >= start_date)

            if end_date:
                mask &= (blocked_until <= end_date)

            if only_active:
                mask &= (blocked_from >= datetime.today()) & (datetime.today() <= blocked_until)

        if show_available:
            mask = (~mask)

        return Dataset(self.data[mask])

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

        blocked_from = pd.to_datetime(self.data['blockedFrom'])
        blocked_until = pd.to_datetime(self.data['blockedUntil'].copy().replace('unlimited', pd.Timestamp('2099-12-31')))

        mask = blocked_from.dt.weekday.isin(weekday_numbers)

        if only_active:
            mask &= (blocked_from >= datetime.today()) & (datetime.today() <= blocked_until)

        return Dataset(self.data[mask])

    def to_df(self, copy=False) -> pd.DataFrame:
        if copy:
            return self.data.copy()
        else:
            return self.data
        
    def to_dict(self, copy=False) -> pd.DataFrame:
        if copy:
            return self.data.to_dict().copy()
        else:
            return self.data.to_dict()

    def get_users(self, user_names: list[str] = [], user_ids: list[int] = [])  -> Dataset:
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
        return Dataset(self.data[self.data['userId'].isin(user_ids) & self.data['userName'].isin(user_names)])

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
        return Dataset(self.data[self.data['roomName'].isin(room_names) | self.data['roomId'].isin(room_ids)])

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
        return Dataset(self.data[self.data["deskId"].isin(desk_ids)])
    
    def group_bookings(self, 
                       by, 
                       aggregation = None, 
                       aggregation_treshhold = 0, 
                       granularity: Optional[Literal["day", "week", "month"]] = None,
                       granularity_aggregation = None):

        grouped_data = self.data.groupby(by)
        print(grouped_data.count())
        if aggregation:
            grouped_data = grouped_data.agg((aggregation, aggregation))
            grouped_data = grouped_data[grouped_data['count'] >= aggregation_treshhold]

        return Dataset(grouped_data)

    def sort_bookings(self, by, ascending=False):
        sorted_data = self.data.sort_values(by=by, ascending=ascending)

        return Dataset(sorted_data)

    # def add_granularity(self, gra):
    #     self.data[]

    def add_day(self):
        expand_fixed_bookings()

        fixed["workdays"] = fixed.apply(lambda row: pd.date_range(row[start_col], row[end_col], freq='B').date, axis=1)
        fixed = fixed.explode("workdays")
        fixed[start_col] = fixed["workdays"]
        fixed[end_col] = fixed["workdays"]
        fixed = fixed.drop(columns=["workdays"]).reset_index(drop=True)

        self.data["day"] = 

    # def add_cw(self):
    #     self.data["cw"] = pd.to_datetime(self.data['blockedFrom']).dt.isocalendar().week

    # def add_month(self):
    #     self.data["month"] = pd.to_datetime(self.data['blockedFrom']).dt.isocalendar().week

if __name__ == "__main__":
    data = create_dataset()
    #dataset.to_csv("OpTisch.csv", index=False)  # Save dataset to CSV without index
    # Some manipulation to showcase the usage
    # Manipulation functions are staticmethods to make it more generic usable
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 5, 21)
    data_timeframe = data.get_timeframe(start_date=start_date, end_date=end_date, show_available=False).to_df()
    print(data_timeframe[data_timeframe["variableBooking"] == 0])
    
    data_days = data_timeframe.get_days(weekdays=["monday", "wednesday"])
    data_rooms = data_days.get_rooms(room_names=["Dechbetten", "Westenviertel"], room_ids=[2, 9, 5])
    data_desks = data_rooms.get_desks(desk_ids=[5, 9, 12])
