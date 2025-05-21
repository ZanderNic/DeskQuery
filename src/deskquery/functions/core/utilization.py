# std-lib import
from typing import Optional, List
from datetime import datetime

# third party imports
import pandas as pd

# project imports
from deskquery.data.dataset import Dataset


def get_utilization(
        overall: bool = False, 
        by_room: bool = False, 
        room: Optional[str] = None, 
        weekday: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
) -> None:
    """
    Returns desk utilization based on provided filters.

    Args:
        overall: If True, returns overall utilization across all desks.
        by_room: If True, returns utilization per room.
        room: Specific room to filter utilization for. If None, includes all rooms.
        weekday: List of weekdays to consider in the analysis.
        start_date: Start of the period to analyze. If None, uses current date.
        end_date: End of the period to analyze. If None, uses current date.

    Returns:
        The average utilization of the deks filltered by the filter
    """
    pass


def get_over_under_utilized_desks(
    threshold: float, 
    by_room: Optional[bool] = None, 
    under: bool = False, 
    weekday: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> None:
    """
    Returns desks with usage above or below a specified utilization threshold.

    Args:
        threshold: Utilization threshold as a float (e.g., 0.8 for 80%).
        by_room: If True, aggregates results per room. If None, shows per-desk.
        under: If True, returns desks with utilization below the threshold if false will return desks with utilization above threshold.
        weekday: Weekdays to include in the evaluation.
        start_date: Beginning of the time window. If None, defaults to ###TODO.
        end_date: End of the time window. If None, defaults to today.

    Returns:
       
    """
    pass


def get_daily_utilization_stats(
    by_room: bool = False, 
    by_desc: bool = False,
    weekday: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> None:
    """
    Returns average, minimum, maximum and variance utilization for each weekday.

    Args:
        by_room: If True, computes stats separately per room.
        by_desc: If True, computes stats separately per desk.
        weekday: List of weekdays to include.
        start_date: Start of the evaluation period.
        end_date: End of the evaluation period.

    Returns:
       
    """
    pass


def get_days_above_bellow_threshold(
    threshold: float, 
    bellow: bool = False, 
    weekdays: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None 
)-> None:
    """
    Counts the number of days where utilization exceeds a given threshold.

    Args:
        threshold: Utilization threshold as a float.
        bellow: If True, returns days with utilization below the threshold if false will return days with utilization above threshold.
        weekdays: Days of the week to analyze.
        start_date: Beginning of date range.
        end_date: End of date range.

    Returns:
        
    """
    pass



def detect_utilization_anomalies(
    threshold: float = 0.2, 
    by_room: bool = False, 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> None:
    """
    Detects days or rooms with significant utilization anomalies.

    Args:
        threshold: Minimum deviation from average to be flagged.
        by_room: If True, checks per room.
        start_date: Period start.
        end_date: Period end.

    Returns:
    """
    pass

def get_most_least_booked(data: Dataset, 
                          top_n: int = 1, 
                          include_fixed=False, 
                          top_type='most', 
                          end_cutting_date: Optional[datetime] = datetime.today()) -> dict[str, dict[str, int]]:
    """Gets statistics about most or least booked resources.
    
    Args:
        data: Dataset containing booking information.
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


    data_until_cutting = data.get_timeframe(data, end_date=end_cutting_date)
    data_until_cutting = data_until_cutting.to_df()

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
