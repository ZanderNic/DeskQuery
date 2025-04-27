# std-lib import
from typing import Optional, List, datetim
from datetime import datetime

# 3 party imports

# projekt imports



def get_avg_booking_per_employee(
    granularity: str, 
    weekdays: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> None:
    """
    Calculates the average number of bookings per employee.

    Args:
        granularity: Period unit for average, e.g., 'week' or 'month'.
        weekdays: Days to include in the calculation.
        start_date: Start date of the analysis.
        end_date: End date of the analysis.

    Returns:

    """
    pass


def get_booking_repeat_pattern(
    min_repeat_count: int, 
    weekdays: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> None:
    """
    Identifies users who book the same desks repeatedly.

    Args:
        min_repeat_count: Minimum number of repeated bookings.
        weekdays: Days of interest.
        start_date: Start date.
        end_date: End date.

    Returns:
    """
    pass


def get_booking_clusters(
    distance_threshold: float, 
    co_booking_count_min: int, 
    weekdays: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> None:
    """
    Finds booking clusters, i.e., groups of users who often book nearby desks.

    Args:
        distance_threshold: Spatial proximity to define a cluster.
        co_booking_count_min: Minimum times users must co-book nearby desks.
        weekdays: Days to consider.
        start_date: Start date.
        end_date: End date.

    Returns:

    """
    pass


def get_co_booking_frequencies(
    min_shared_days: int, 
    same_room_only: bool, 
    weekdays: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
)-> None:
    """
    Detects employee pairs who frequently book on the same days.

    Args:
        min_shared_days: Minimum number of shared booking days.
        same_room_only: If True, limits to co-bookings in the same room.
        weekdays: Days to analyze.
        start_date: Start date.
        end_date: End date.

    Returns:
    """
    pass
