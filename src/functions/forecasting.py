# std-lib import
from typing import Optional, List, datetim
from datetime import datetime

# 3 party imports

# projekt imports


### TODO ADD different forcarsting methods like Linear and xx Regression, mybe also ML Options like LSTM  or GRU (will probably dont work)


def estimate_table_needs(
    target_utilization: float, 
    attendance_days: int, 
    employee_count: int, 
    existing_desks: Optional[int] = None, 
    data_for_forcast_start_date: Optional[datetime] = None, 
    data_for_forcast_end_date: Optional[datetime] = None
) -> None:
    """
    Estimates required number of desks to meet a target utilization.

    Args:
        target_utilization: Target average utilization.
        attendance_days: Number of days employees are expected to attend weekly.
        employee_count: Total number of employees considered.
        existing_desks: Number of currently available desks.
        data_for_forcast_start_date: Date to start using historical data.
        data_for_forcast_end_date: Date to end using historical data.

    Returns:
    """
    pass


def forecast_desk_demand(
    current_employee_count: int, 
    weekly_growth_rate: float,
    available_desks: int, 
    target_utilization: float, 
    data_for_forcast_start_date: Optional[datetime] = None, 
    data_for_forcast_end_date: Optional[datetime] = None
) -> None:
    """
    Forecasts desk demand based on employee growth.

    Args:
        current_employee_count: Current number of employees.
        weekly_growth_rate: Weekly employee growth as a percentage.
        available_desks: Total number of desks available.
        target_utilization: Desired desk utilization threshold.
        data_for_forcast_start_date: Historical data start.
        data_for_forcast_end_date: Historical data end.

    Returns:

    """
    pass


def simulate_room_closure(
    room_id: str, 
    reassign_strategy: str, 
    time_closed: Optional[str] = None, 
    data_for_forcast_start_date: Optional[datetime] = None, 
    data_for_forcast_end_date: Optional[datetime] = None
) -> None:
    """
    Simulates what happens if a room is closed.

    Args:
        room_id: Identifier of the room to close.
        reassign_strategy: Strategy to reassign affected bookings (e.g., 'random').
        time_closed: Timeframe of the closure.
        data_for_forcast_start_date: Data window start.
        data_for_forcast_end_date: Data window end.

    Returns:

    """
    pass


def estimate_max_employees_per_room(
    room_id: str, 
    target_utilization: float, 
    average_attendance_days: int
) -> None:
    """
    Estimates maximum employees for a room given a target utilization.

    Args:
        room_id: Identifier for the room.
        target_utilization: Desired utilization rate.
        average_attendance_days: Expected days in office per week.

    Returns:
        None. Useful for space planning.
    """
    pass

