# std-lib import
from typing import Optional, List
from datetime import datetime

# 3 party imports

# projekt imports


def generate_heatmap(
    by_room: bool, 
    resolution: str, 
    weekdays: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> None:
    """
    Generates a heatmap showing desk bookings over time.

    Args:
        by_room: If True, shows heatmap per room.
        resolution: Time resolution of heatmap: 'daily', 'weekly', or 'monthly'.
        weekdays: Days of the week to include.
        start_date: Start date for data.
        end_date: End date for data.

    Returns:

    """
    pass


def generate_plot_interactive(
    by_room: bool, 
    resolution: str, weekdays: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> None:
    """
    Produces an interactive plot of desk booking data.

    Args:
        by_room: If True, plots are grouped by room.
        resolution: Level of temporal detail ('daily', 'weekly', etc.).
        weekdays: Days of interest.
        start_date: Analysis start date.
        end_date: Analysis end date.

    Returns:
    
    """
    pass


def generate_plot(
    by_room: bool, 
    resolution: str, 
    desk: int, 
    weekdays: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> None:
    """
    Creates a plot of desk utilization over time.

    Args:
        by_room: If True, groups data by room.
        resolution: Time granularity.
        desk: Desk ID or 'all' to include all desks.
        weekdays: Relevant weekdays.
        start_date: Starting date.
        end_date: Ending date.

    Returns:

    """
    pass
