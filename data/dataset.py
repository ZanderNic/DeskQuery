#!/usr/bin/env python 
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

pd.set_option('future.no_silent_downcasting', True)

class Dataset:
    def __init__(self, path: str):
        # Load all sheets from the Excel file into a dictionary of DataFrames
        self.sheets = pd.read_excel(path, sheet_name=None)
        self._rename_columns()

        # there is a missing value in the database therefore fill it and convert the columns to ints afterwards (from float due to the NaN value)
        self.sheets["fixedBooking"].loc[self.sheets["fixedBooking"]["id"] == 5, "deskNumber"] = 1
        self.sheets["fixedBooking"]["deskNumber"] = self.sheets["fixedBooking"]["deskNumber"].astype(int)
        # userIds are off by one in the database therefore incremente it
        self.sheets["variableBooking"]["userId"] += 1

        self.desk_room_mapping: pd.DataFrame = self.get_desk_room_mapping()
        self.data: Optional[pd.DataFrame] = self.create_dataset()

    def _rename_columns(self) -> pd.DataFrame:
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

        for sheet_name, data in self.sheets.items():
            # Strip trailing whitespaces from all column names
            data.columns = data.columns.str.strip()
            # Replace all occurrences of "null" or any string that consists only of whitespaces with NaN
            # Use a regex sind there are many trailing whitespaces and so on
            self.sheets[sheet_name] = data.replace(r'^\s*(null|\s*)\s*$', np.nan, regex=True).infer_objects(copy=False)
            self.sheets[sheet_name] = self.sheets[sheet_name].rename(columns=column_mapping)

    def __str__(self):
        return str(self.data)

    def to_csv(self, name, index=False):
        if isinstance(self.data, pd.DataFrame):
            self.data.to_csv(name, index=index)  # Save dataset to CSV without index


    def get_desk_room_mapping(self) -> pd.DataFrame:
        """Creates a mapping between desks and rooms"""
        desk_room_mapping = self.sheets["fixedBooking"][["id", "deskNumber", "roomId"]].rename(columns={"id": "deskId"}).astype(int)
        desk_room_mapping = pd.merge(desk_room_mapping, self.sheets["room"], how="left", left_on="roomId", right_on="id").drop(columns="id")
        # Room in the database looks like Raum "Dechbetten" but we just wanna stick with Dechbetten (way easier to handle later)
        desk_room_mapping['roomName'] = desk_room_mapping['roomName'].str.extract(r'"([^"]+)"', expand=False)

        return desk_room_mapping

    def join_fixed_bookings(self):
        data_fixed = pd.merge(self.sheets["fixedBooking"], self.sheets["user"], how="left", left_on="userId", right_on="ID").drop(columns=["ID"])
        data_fixed = pd.merge(data_fixed, self.desk_room_mapping[['roomName', 'deskId']], left_on='id', right_on="deskId", how='left')
        data_fixed["variableBooking"] = 0 # Indicate fixed bookings
        # According to Mr. Fraunhofer, these are leftover entries from old bookings. Therefore we just drop them.
        data_fixed = data_fixed.dropna(subset=['userId', 'blockedUntil'], how='all')
        data_fixed.loc[data_fixed['blockedUntil'].isna(), 'blockedUntil'] = 'unlimited'

        return data_fixed

    def join_variable_bookings(self):
        data_variable = pd.merge(self.sheets["variableBooking"], self.sheets["user"], how="left", left_on="userId", right_on="ID").drop(columns=["ID"])
        data_variable = pd.merge(data_variable, self.desk_room_mapping, on='deskId', how='left')
        # Since variable bookings are just for one day we fill the blockeduntil column with the same value to make comparions later on easier
        data_variable["blockedUntil"] = data_variable["blockedFrom"]
        data_variable["variableBooking"] = 1 # Indicate variable bookings

        return data_variable

    def create_dataset(self) -> pd.DataFrame:
        """This Function denormalizes the excel file to make it easier to handle.

        Args:
            path (str, optional): Path of the excel file. Defaults to "OpTisch_anonymisiert.xlsx".

        Returns:
            pd.DataFrame: A denormalized dataset
        """
        data_fixed = self.join_fixed_bookings()
        data_variable = self.join_variable_bookings()

        data = pd.concat([data_fixed, data_variable], axis=0).rename(columns={"id": "bookingId"})

        return data

    @staticmethod
    def get_timeframe(data: pd.DataFrame, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, show_available: bool = False, only_active: bool = False):
        """Filters desk data based on time constraints and availability status.
        
        Filters the DataFrame to show desks that are either blocked or available within
        the specified time period, with options to show only currently active blocks.

        Args:
            data: DataFrame containing desk data with blocking information.
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
        mask = pd.Series(True, index=data.index)
        
        if start_date or end_date or only_active:
            blocked_from = pd.to_datetime(data['blockedFrom'])
            # tread unlimited endtime as a very high number to make the comparison easier later
            blocked_until = pd.to_datetime(data['blockedUntil'].copy().replace('unlimited', datetime(2099, 12, 31)))

            if start_date:
                mask &= (blocked_from >= start_date)

            if end_date:
                mask &= (blocked_until <= end_date)

            if only_active:
                mask &= (blocked_from >= datetime.today()) & (datetime.today() <= blocked_until)

        if show_available:
            mask = (~mask)

        return data[mask]

    @staticmethod
    def get_days(data, weekdays: list[str], only_active: bool = False) -> pd.DataFrame:
        """Filters desk data based on specific weekdays when desks are blocked.
        
        Args:
            data: DataFrame containing desk blocking information.
            weekdays: List of weekday names to filter (e.g., ['monday', 'tuesday']).
                Valid values: 'monday', 'tuesday', 'wednesday', 'thursday',
                'friday', 'saturday', 'sunday' (case-sensitive)
            only_active: If True, returns only blocks that are currently active
                (today is between blockedFrom and blockedUntil).
                
        Returns:
            Filtered DataFrame containing only blocks starting on specified weekdays.
            
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

        blocked_from = pd.to_datetime(data['blockedFrom'])
        blocked_until = pd.to_datetime(data['blockedUntil'].copy().replace('unlimited', pd.Timestamp('2099-12-31')))

        mask = blocked_from.dt.weekday.isin(weekday_numbers)

        if only_active:
            mask &= (blocked_from >= datetime.today()) & (datetime.today() <= blocked_until)

        return data[mask]

    @staticmethod
    def get_users(data: pd.DataFrame, user_names: list[str] = [], user_ids: list[int] = []) -> pd.DataFrame:
        """Filters desk data based on user names or IDs.
        
        Args:
            data: DataFrame containing desk booking information.
            user_names: List of user names to filter (OR condition).
            user_ids: List of user IDs to filter (OR condition).
                
        Returns:
            Filtered DataFrame where either user_name or user_id matches.
            
        Example:
            >>> get_users(df, user_names=['Hiro Tanaka', 'Emma Brown'], user_ids=[5, 3])
            # Returns desks booked by either Hiro Tanaka, Emma Brown, or users with ID 5 or 3
        """
        return data[data['userId'].isin(user_ids) & data['userName'].isin(user_names)]

    @staticmethod
    def get_rooms(data: pd.DataFrame, room_names: list[str] = [], room_ids: list[int] = []) -> pd.DataFrame:
        """Filters desk data based on room names or IDs.
        
        Args:
            data: DataFrame containing room information.
            room_names: List of room names to filter (OR condition).
            room_ids: List of room IDs to filter (OR condition).
                
        Returns:
            Filtered DataFrame where either room_name or room_id matches.
            
        Example:
            >>> get_rooms(df, room_names=['Stadtamhof'], room_ids=[50])
            # Returns desks in either 'Stadtamhof' or room with ID 50
        """
        return data[data['roomName'].isin(room_names) | data['roomId'].isin(room_ids)]

    @staticmethod
    def get_desks(data: pd.DataFrame, desk_ids: list[int] = []):
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
        return data[data["deskId"].isin(desk_ids)]

    @staticmethod
    def get_most_least_booked(data: pd.DataFrame, top_n: int = 1, include_fixed=False, top_type='most', end_cutting_date: Optional[datetime] = datetime.today()) -> dict[str, dict[str, int]]:
        """Gets statistics about most or least booked resources.
        
        Args:
            data: DataFrame containing booking information.
            top_n: Number of top items to return for each category.
            include_fixed: If True, counts each day of fixed bookings separately.
                If False, counts each booking block as one occurrence.
            top_type: Either 'most' (for most booked) or 'least' (for least booked).
            end_cutting_date: When the booking are cut (mainly today to prevent problems through cancelation and no outweighting of fixedbookings)
                
        Returns:
            Dictionary with four metrics:
            - {top_type}_booked_room: Most/least booked rooms
            - {top_type}_booked_desk: Most/least booked desks (formatted as 'roomName_deskNumber')
            - {top_type}_booked_user: Most/least booked users
            - {top_type}_booked_day: Most/least booked days of week
            
        Raises:
            ValueError: If top_type is neither 'most' nor 'least'.
            
        Example:
            >>> get_most_least_booked(df, top_n=3, include_fixed=True, top_type='most')
            # Returns dictionary with top 3 most booked items in each category,
            # counting each day of fixed bookings separately
        """
        def get_counts(series: pd.Series, top_n: int, top_type: str):
            if top_type == 'most':
                return series.value_counts().head(top_n)
            elif top_type == 'least':
                return series.value_counts().tail(top_n)
            else:
                raise ValueError("top_type must be 'most' or 'least'")

        def expand_fixed_bookings(data, start_col="blockedFrom", end_col="blockedUntil"):
            """
            Expands fixed bookings over all business days between start and end dates.

            Parameters:
                data (pd.DataFrame): The input DataFrame containing booking information.
                start_col (str): The name of the column representing the booking start date.
                end_col (str): The name of the column representing the booking end date.

            Returns:
                pd.DataFrame: A DataFrame with fixed bookings expanded by business day
            """
            variable = data[data["variableBooking"] == 1]
            fixed = data[data["variableBooking"] == 0].copy()

            fixed["workdays"] = fixed.apply(lambda row: pd.date_range(row[start_col], row[end_col], freq='B').date, axis=1)
            fixed = fixed.explode("workdays")
            fixed[start_col] = fixed["workdays"]
            fixed[end_col] = fixed["workdays"]
            fixed = fixed.drop(columns=["workdays"]).reset_index(drop=True)
            
            return pd.concat([fixed, variable], ignore_index=True)

        data_until_cutting = Dataset.get_timeframe(data, end_date=end_cutting_date)

        if include_fixed:
            # replace "unlimited" with end_cutting_date to prevent issues later
            data_until_cutting = data.replace("unlimited", end_cutting_date)
            data_until_cutting = expand_fixed_bookings(data_until_cutting)
        else:
            data_until_cutting = data_until_cutting[data_until_cutting["variableBooking"] == 1]

        most_least_booked_room = get_counts(data_until_cutting['roomName'], top_n, top_type)
        # Do it like this to have a more human readable result (room with desknumber seems to be better than just deskId)
        room_desk = data_until_cutting['roomName'] + '_' + data_until_cutting['deskNumber'].astype(str)
        most_least_booked_desk = get_counts(room_desk, top_n, top_type)
        most_least_booked_user = get_counts(data_until_cutting['userName'], top_n, top_type)
        # blockedFrom is sufficent since expand_fixed_bookings change the data in the way that blockedFrom and blockedUntil are always the same
        most_least_booked_day = get_counts(pd.to_datetime(data_until_cutting["blockedFrom"]).dt.day_name(), top_n, top_type)

        return {
            f'{top_type}_booked_room': most_least_booked_room.to_dict(),
            f'{top_type}_booked_desk': most_least_booked_desk.to_dict(),
            f'{top_type}_booked_user': most_least_booked_user.to_dict(),
            f'{top_type}_booked_day': most_least_booked_day.to_dict()
        }



if __name__ == "__main__":
    dataset = Dataset(path="OpTisch_anonymisiert.xlsx")
    dataset.to_csv("OpTisch.csv", index=False)  # Save dataset to CSV without index
    # Some manipulation to showcase the usage
    # Manipulation functions are staticmethods to make it more generic usable
    data = dataset.data
    start_date = datetime(2024, 3, 14)
    end_date = datetime(2024, 3, 25)
    data_timeframe = dataset.get_timeframe(data, start_date=start_date, end_date=end_date, show_available=False)
    data_days = dataset.get_days(data_timeframe, weekdays=["monday", "wednesday"])
    data_least_booked = dataset.get_most_least_booked(data_timeframe, top_n=4, top_type="least", include_fixed=False)
    data_rooms = dataset.get_rooms(data, room_names=["Dechbetten", "Westenviertel"], room_ids=[2, 9, 5])
    data_desks = dataset.get_desks(data, desk_ids=[5, 9, 12])
    print(data_least_booked)
