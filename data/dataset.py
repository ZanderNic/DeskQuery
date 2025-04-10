#!/usr/bin/env python 
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

pd.set_option('future.no_silent_downcasting', True)

def rename_columns(data: pd.DataFrame) -> pd.DataFrame:
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
        "id": "bookingId"
    }
    return data.rename(columns=column_mapping)

def get_desk_room_mapping(fixedBooking_sheet: pd.DataFrame, room_sheet: pd.DataFrame) -> pd.DataFrame:
    desk_room_mapping = fixedBooking_sheet[["bookingId", "deskNumber", "roomId"]].sort_values(by=["roomId", "deskNumber"]).rename(columns={"bookingId": "deskId"}).astype(int)
    desk_room_mapping = pd.merge(desk_room_mapping, room_sheet, how="left", left_on="roomId", right_on="bookingId").drop(columns="bookingId")
    desk_room_mapping['roomName'] = desk_room_mapping['roomName'].str.extract(r'"([^"]+)"', expand=False)

    return desk_room_mapping

def create_dataset(path: str = "OpTisch_anonymisiert.xlsx") -> pd.DataFrame:
    """This Function denormalizes the excel file to make it easier to handle.

    Args:
        path (str, optional): Path of the excel file. Defaults to "OpTisch_anonymisiert.xlsx".
        num_sheets (int, optional): Number of sheets in the excel file. Defaults to 4.

    Returns:
        pd.DataFrame: A denormalized dataset
    """
    # Load all sheets from the Excel file into a dictionary of DataFrames
    sheets = pd.read_excel(path, sheet_name=None)
    
    for sheet_name, data in sheets.items():
        # Strip trailing whitespaces from all column names
        data.columns = data.columns.str.strip()
        # Replace all occurrences of "null" or any string that consists only of whitespaces with NaN
        # Use a regex sind there are many trailing whitespaces and so on
        sheets[sheet_name] = data.replace(r'^\s*(null|\s*)\s*$', np.nan, regex=True).infer_objects(copy=False)
        sheets[sheet_name] = rename_columns(sheets[sheet_name])

    sheets["fixedBooking"].loc[sheets["fixedBooking"]["bookingId"] == 5, "deskNumber"] = 1
    sheets["fixedBooking"]["deskNumber"] = sheets["fixedBooking"]["deskNumber"].astype(int)
    sheets["variableBooking"]["userId"] += 1

    desk_room_mapping = get_desk_room_mapping(sheets["fixedBooking"], sheets["room"])
    # fixed bookings with room
    data_fixed = pd.merge(sheets["fixedBooking"], sheets["user"], how="left", left_on="userId", right_on="ID").drop(columns=["ID"])
    data_fixed = pd.merge(data_fixed, desk_room_mapping[['roomName', 'deskId']], left_on='bookingId', right_on="deskId", how='left')
    data_fixed["variableBooking"] = 0 # Indicate fixed bookings
    # According to Mr. Fraunhofer, these are leftover entries from old bookings. Therefore we drop them    
    data_fixed = data_fixed.dropna(subset=['blockedFrom', 'userId', 'blockedUntil'], how='all')
    data_fixed.loc[data_fixed['blockedUntil'].isna(), 'blockedUntil'] = 'unlimited'

    # variable bookings with room
    data_variable = pd.merge(sheets["variableBooking"], sheets["user"], how="left", left_on="userId", right_on="ID").drop(columns=["ID"])
    data_variable = pd.merge(data_variable, desk_room_mapping, on='deskId', how='left')
    data_variable["blockedUntil"] = data_variable["blockedFrom"]
    data_variable["variableBooking"] = 1 # Indicate variable bookings

    data = pd.concat([data_fixed, data_variable], axis=0)

    return data

def get_days(data, weekdays: list[str], only_active: Optional[bool] = False) -> pd.DataFrame:
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

def get_most_least_booked(data: pd.DataFrame, top_n: int = 1, include_fixed=False, top_type='most') -> dict[str, dict[str, int]]:
    """Gets statistics about most or least booked resources.
    
    Args:
        data: DataFrame containing booking information.
        top_n: Number of top items to return for each category.
        include_fixed: If True, counts each day of fixed bookings separately.
            If False, counts each booking block as one occurrence.
        top_type: Either 'most' (for most booked) or 'least' (for least booked).
            
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
    
    most_least_booked_room = get_counts(data['roomName'], top_n, top_type)
    # Do it like this to have a more human readable resultv (room with desknumber seems better than just deskId)
    room_desk = data['roomName'] + '_' + data['deskNumber'].astype(str)
    most_least_booked_desk = get_counts(room_desk, top_n, top_type)
    most_least_booked_user = get_counts(data['userName'], top_n, top_type)

    # TODO: unlimited outweight insanly how to encounter it? maybe just until today?
    # TODO: We have to do the same for the other things like rooms so count them for every day they are booked not just once
    blocked_from = pd.to_datetime(data['blockedFrom'])
    blocked_until = pd.to_datetime(data['blockedUntil'].copy().replace('unlimited', datetime(2099, 12, 31)))

    if include_fixed:
        all_days = []
        for i in range(len(blocked_from)):
            all_days.extend(pd.date_range(start=blocked_from.iloc[i], end=blocked_until.iloc[i], freq='D').day_name())
        most_least_booked_day = get_counts(pd.Series(all_days), top_n, top_type)
    else:
        most_least_booked_day = get_counts(blocked_from.dt.day_name(), top_n, top_type)

    return {
        f'{top_type}_booked_room': most_least_booked_room.to_dict(),
        f'{top_type}_booked_desk': most_least_booked_desk.to_dict(),
        f'{top_type}_booked_user': most_least_booked_user.to_dict(),
        f'{top_type}_booked_day': most_least_booked_day.to_dict()
    }

def get_timeframe(data: pd.DataFrame, start_date: datetime, end_date: Optional[datetime] = None, show_available: bool = False, only_active: bool = False):
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

if __name__ == "__main__":
    data = create_dataset()
    data.to_csv("OpTisch.csv", index=False)  # Save dataset to CSV without index

    # Some manipulation to showcase the usage
    start_date = datetime(2024, 3, 14)
    end_date = datetime(2024, 3, 25)
    data_timeframe = get_timeframe(data, start_date=start_date, show_available=True)
    data_days = get_days(data_timeframe, weekdays=["monday", "wednesday"])
    data_least_booked = get_most_least_booked(data, top_n=4, top_type="least")
    data_rooms = get_rooms(data, room_names=["Dechbetten", "Westenviertel"], room_ids=[2, 9, 5])
    data_desks = get_desks(data, desk_ids=[5, 9, 12])
