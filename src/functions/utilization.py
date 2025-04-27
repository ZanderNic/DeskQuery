# std-lib import
from typing import Optional, List, datetim
from datetime import datetime

# 3 party imports


# projekt imports



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

