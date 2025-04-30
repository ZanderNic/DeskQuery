# std-lib imports
from typing import Optional, List
from datetime import datetime

# 3 party imports

# projekt imports



def simulate_policy(
    policy_type: str, 
    mandatory_day: Optional[str] = None, 
    min_days_per_week: Optional[int] = None, 
    employee_count: Optional[int] = None, 
    simulation_weeks: int = 4
) -> None:
    """
    Simulates the impact of a given policy on desk utilization.

    Args:
        policy_type: Type of policy, e.g., 'mandatory_day', 'min_days_per_week'.
        mandatory_day: Specific weekday to enforce attendance on (if applicable).
        min_days_per_week: Minimum number of days employees must attend in a week.
        employee_count: Number of employees. Defaults to current count.
        simulation_weeks: Number of weeks to run the simulation.

    Returns:

    """
    pass


def detect_policy_violations(
    policy_type: str, 
    min_days_per_week: Optional[int] = None, 
    mandatory_day: Optional[str] = None, 
    weekdays: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> None:
    """
    Identifies employees who do not comply with a given policy.

    Args:
        policy_type: The policy being evaluated.
        min_days_per_week: Required minimum days per week for attendance.
        mandatory_day: Required attendance day if applicable.
        weekdays: Days of the week considered.
        start_date: Start of the period to evaluate.
        end_date: End of the period to evaluate.

    Returns:

    """
    pass


def suggest_balanced_utilization_policy(
    target_utilization: float, 
    max_mandatory_days: int = 2
) -> None:
    """
    Suggests an attendance policy to achieve a more balanced desk utilization.

    This function analyzes historical booking patterns and simulates different attendance 
    strategies to recommend a policy that helps distribute occupancy more evenly 
    across weekdays and rooms.

    Args:
        target_utilization: Desired average utilization rate per weekday, 
            expressed as a float between 0 and 1 (e.g., 0.75 for 75%).
        max_mandatory_days: Maximum number of mandatory office days per week 
            that should be imposed by the suggested policy. 
            This parameter limits how strict the policy recommendation can be.

    Returns:
       
    Notes:
        The function may store or output the suggestion elsewhere (e.g., in a report, log, or user interface).
    """
    pass


def compare_utilization_before_after_policy(
    
):
    pass # TODO