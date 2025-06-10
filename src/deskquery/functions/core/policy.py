# std-lib imports
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from collections import Counter

# 3 party imports
import pandas as pd
import numpy as np

# projekt imports
from deskquery.data.dataset import Dataset
from deskquery.functions.types import FunctionRegistryExpectedFormat, PlotForFunction
from deskquery.functions.core.helper.plot_helper import generate_barchart, generate_lineplot


def simulate_policy(
    data: Dataset,
    policy: Dict,
    exceptions: Optional[Dict[int, Dict]] = None,
    random_assignments: Optional[List[Tuple[int, Dict]]] = None,
    num_weeks: int = 100,
    weekdays: List[str] = ["Mo", "Di", "Mi", "Do", "Fr"], # FIXME: Change to English
    plotable: bool = True
) -> FunctionRegistryExpectedFormat:
    """
    Assigns policies and simulates the weekly attendance of all employees based on them. A policy is a dict of the following parameters 
    which are included in the policy, exceptions (if given) and random_assignments (if given):

        timeframe (str): Policy timeframe (currently only "week" is supported).
        fixed_days (Optional[List[str]]): Days that are always selected.
        choseable_days (Optional[List[str]]): Days from which a fixed number is chosen.
        number_choseable_days (Optional[int]): Number of days to pick from `choseable_days`.
        number_days (Optional[int]): Target total number of days.
        more_days_allowed (bool): If True, adds additional days based on attendance.

    Args:
        data (Dataset): The dataset containing booking data.
        policy (Dict): Default policy parameters.
        exceptions (Optional[Dict[int, Dict]]): Special policy rules for certain employee IDs.
        random_assignments (Optional[List[Tuple[int, Dict]]]): List of tuples (number_of_employees, policy_dict) for random policy assignment.
        num_weeks (int): Number of weeks over which the attendance is simulated.
        weekdays (List[str]): List of weekdays used in the simulation, e.g., ["Mo", "Di", "Mi", "Do", "Fr"].
        plotable (bool): If called from another function set to False

    Returns:
        dict[str, object]: Dictionary containing the average total attendance (Monday to Sunday) across all employees and potentially other metrics.
    """
    attendances = load_attendance_profiles(data=data, weekdays=weekdays)
    worker_ids = list(attendances.keys())
    policies: Dict[int, Dict] = {}
    assigned_ids = set()

    if exceptions:
        for worker_id, policy_kwargs in exceptions.items():
            policies[worker_id] = policy_kwargs
            assigned_ids.add(worker_id)

    if random_assignments:
        unassigned_ids = list(set(worker_ids) - assigned_ids)
        for amount, policy_kwargs in random_assignments:
            if amount > len(unassigned_ids):
                raise ValueError(f"Not enough employees for {amount} of this policy")
            selected_ids = np.random.choice(unassigned_ids, amount, replace=False).tolist()
            for worker_id in selected_ids:
                policies[worker_id] = policy_kwargs
                assigned_ids.add(worker_id)
                unassigned_ids.remove(worker_id)

    for worker_id in worker_ids:
        if worker_id not in policies:
            policies[worker_id] = policy

    all_weeks = []
    for worker_id, attendance in attendances.items():
        policy = policies[worker_id]
        simulated = [draw_days(attendance, **policy, weekdays=weekdays) for _ in range(num_weeks)]
        averaged = average_simulated_weeks(simulated)
        all_weeks.append(list(averaged))

    total_attendance = np.sum(all_weeks, axis=0)

    if plotable:
        final_data: Dict[str, Dict[str, float]] = {
            "total_attendance": dict(zip(weekdays, total_attendance))
        }

        plot = PlotForFunction(
            default_plot=generate_barchart(
                data=final_data,
                title=f"Attendance per weekday",
                xaxis_title="Weekday",
                yaxis_title="Attendance"
            ),
            available_plots=[generate_barchart]
        )

        return FunctionRegistryExpectedFormat(data=final_data, plot=plot)

    return total_attendance


def detect_policy_violations(
    data: Dataset,
    policy: Dict,
    exceptions: Optional[Dict[int, Dict]] = None,
    random_assignments: Optional[List[Tuple[int, Dict]]] = None,
    weekdays: List[str] = ["Mo", "Di", "Mi", "Do", "Fr"], # FIXME: Change to English
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None,
    only_stats: bool = False
) -> FunctionRegistryExpectedFormat:
    """
    Takes a policy and searches the data for violations. A policy is a dict of the following parameters 
    which are included in the policy, exceptions (if given) and random_assignments (if given):

        timeframe (str): Policy timeframe (currently only "week" is supported).
        fixed_days (Optional[List[str]]): Days that are always selected.
        choseable_days (Optional[List[str]]): Days from which a fixed number is chosen.
        number_choseable_days (Optional[int]): Number of days to pick from `choseable_days`.
        number_days (Optional[int]): Target total number of days.
        more_days_allowed (bool): If True, adds additional days based on attendance.

    Args:
        data (Dataset): The dataset containing booking data.
        policy (Dict): Default policy parameters.
        exceptions (Optional[Dict[int, Dict]]): Targeted special rules for certain employee IDs.
        random_assignments (Optional[List[Tuple[int, Dict]]]): List of tuples (number_of_employees, policy dict) for random assignment.
        weekdays (List[str]): Days of the week considered, e.g., ["Mo", "Di", "Mi", "Do", "Fr"].
        start_date (Optional[datetime]): Start date of the period to evaluate. Defaults to earliest date in data if None.
        end_date (Optional[datetime]): End date of the period to evaluate. Defaults to latest date in data if None.
        only_stats (bool): If True, returns only aggregated weekly violation counts instead of detailed per-user violations.

    Returns:
        dict[str, object]: Dictionary containing either per-user violations or aggregated weekly violation statistics.
    """

    attendances = load_attendances(data=data)

    user_ids = list(attendances.keys())
    assigned_ids = set()
    policies: Dict[int, Dict] = {}

    if exceptions:
        for worker_id, policy_kwargs in exceptions.items():
            policies[worker_id] = policy_kwargs
            assigned_ids.add(worker_id)

    if random_assignments:
        unassigned_ids = list(set(user_ids) - assigned_ids)
        for amount, policy_kwargs in random_assignments:
            if amount > len(unassigned_ids):
                raise ValueError(f"Not enough employees for {amount} of this policy")
            selected_ids = np.random.choice(unassigned_ids, amount, replace=False).tolist()
            for worker_id in selected_ids:
                policies[worker_id] = policy_kwargs
                assigned_ids.add(worker_id)
                unassigned_ids.remove(worker_id)

    for worker_id in user_ids:
        if worker_id not in policies:
            policies[worker_id] = policy

    all_dates = [date for user in attendances.values() for date in user]
    min_date = min(all_dates)
    max_date = max(all_dates)
    start_date = start_date or min_date
    end_date = end_date or max_date

    violations: Dict[int, List[Dict]] = {}
    weekly_stats: Dict[str, Dict[str, int]] = {}

    current = start_date
    one_week = timedelta(days=7)

    while current <= end_date:
        week_dates = [(current + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        week_day_names = [(current + timedelta(days=i)).strftime("%A") for i in range(7)]
        week_label = current.strftime("%Y-%m-%d")

        for user_id in user_ids:
            user_policy = policies[user_id]
            fixed_days = user_policy.get("fixed_days", [])
            chooseable_days = user_policy.get("choseable_days", [])
            number_chooseable = user_policy.get("number_choseable_days")
            number_days = user_policy.get("number_days")
            more_days_allowed = user_policy.get("more_days_allowed", False)

            user_data = attendances[user_id]
            attended_days = [week_day_names[i] for i, d in enumerate(week_dates) if d in user_data]

            broken_rules = []

            for day in fixed_days:
                if day in weekdays and day not in attended_days:
                    broken_rules.append(f"Missing fixed day: {day}")

            if number_chooseable is not None and chooseable_days:
                chosen = [d for d in attended_days if d in chooseable_days]
                if len(chosen) < number_chooseable:
                    broken_rules.append(f"Too few chooseable days: {len(chosen)} < {number_chooseable}")

            if number_days is not None:
                if len(attended_days) < number_days:
                    broken_rules.append(f"Too few days: {len(attended_days)} < {number_days}")
                if not more_days_allowed and len(attended_days) > number_days:
                    broken_rules.append(f"Too many days: {len(attended_days)} > {number_days}")

            if broken_rules:
                if only_stats:
                    for rule in broken_rules:
                        if rule.startswith("Missing fixed day"):
                            rule_key = "Missing fixed day"
                        elif rule.startswith("Too few chooseable days"):
                            rule_key = "Too few chooseable days"
                        elif rule.startswith("Too few days"):
                            rule_key = "Too few days"
                        elif rule.startswith("Too many days"):
                            rule_key = "Too many days"
                        else:
                            rule_key = rule

                        if rule_key not in weekly_stats:
                            weekly_stats[rule_key] = {}
                        weekly_stats[rule_key][week_label] = weekly_stats[rule_key].get(week_label, 0) + 1
                else:
                    if user_id not in violations:
                        violations[user_id] = []
                    violations[user_id].append({
                        "time": week_label,
                        "rule_broken": "; ".join(broken_rules)
                    })

        current += one_week

    if only_stats:
        plot = PlotForFunction(default_plot=generate_lineplot(data=weekly_stats,
                                                            title=f"Weekly policy violations",
                                                            xaxis_title="Date",
                                                            yaxis_title="Violations"),
                            available_plots=[generate_lineplot])

        return FunctionRegistryExpectedFormat(data=weekly_stats, plot=plot)
    
    return FunctionRegistryExpectedFormat(data=weekly_stats, plot=PlotForFunction(default_plot=None, available_plots=[]))


####### Helpers ###########################################################################################################################################################################

def expand_fixed_bookings(
    fixed: Dataset
) -> Dataset:
    """
    Creates daily entries for the fixed bookings
    """
    expanded_rows = []

    for _, row in fixed.iterrows():
        start = row["blockedFrom"].date()
        end = row["blockedUntil"].date()
        for day in pd.date_range(start=start, end=end, freq="D"):
            new_row = row.copy()
            new_row["blockedFrom"] = day
            new_row["blockedUntil"] = day
            expanded_rows.append(new_row)

    fixed_expanded = pd.DataFrame(expanded_rows)
    return fixed_expanded


def create_attendance_dataframe(
    data: Dataset,
    start_date: datetime.date,
    end_date: datetime.date
) -> pd.DataFrame:
    """
    Create a dataframe that contains all attendances
    """
    data["blockedFrom"] = pd.to_datetime(data["blockedFrom"], errors="coerce")
    data["blockedUntil"] = pd.to_datetime(data["blockedUntil"], errors="coerce")

    data = data[
        (data["blockedFrom"].dt.date >= start_date) &
        (data["blockedFrom"].dt.date <= end_date)
    ]

    attendance_rows = []
    for _, row in data.iterrows():
        start = max(row["blockedFrom"].normalize(), pd.Timestamp(start_date))
        end = min(row["blockedUntil"].normalize(), pd.Timestamp(end_date))
        for day in pd.date_range(start=start, end=end):
            attendance_rows.append({
                "worker_id": row["userId"],
                "date": day
            })

    df_attendance = pd.DataFrame(attendance_rows)
    return df_attendance


def load_attendance_profiles(
    data: Dataset,
    lag: int = 90,
    weekdays: List[str] = ["Mo", "Di", "Mi", "Do", "Fr"]
) -> List[Dict[float, List[float]]]:
    """
    Creates attendance profiles for all workers. An attendance profile is the average attendance for all the weekdays. 

    Args:
        data (Dataset): The dataset containing booking data.
        lag: Time frame which is used to create the attendance profiles.
        weekdays: Days of the week that should be contained in the attendance profile.

    Returns:
        List of dictionaries of the form: {worker_id: [average attendance monday, ..., average attendance sunday]}
    """
    weekday_map = {"Mo": 0, "Di": 1, "Mi": 2, "Do": 3, "Fr": 4, "Sa": 5, "So": 6}  # FIXME: Change to English
    selected_weekdays = [weekday_map[day] for day in weekdays]

    data["blockedFrom"] = pd.to_datetime(data["blockedFrom"], errors="coerce")

    variable = data[data["variableBooking"] == 1].copy()
    end_date = variable["blockedFrom"].max().date()

    data["blockedUntil"] = data["blockedUntil"].astype(str)
    data.loc[data["blockedUntil"] == "unlimited", "blockedUntil"] = pd.Timestamp(end_date)
    data["blockedUntil"] = pd.to_datetime(data["blockedUntil"], errors="coerce")

    fixed = data[data["variableBooking"] == 0].copy()
    fixed_expanded = expand_fixed_bookings(fixed)

    data = pd.concat([fixed_expanded, variable], ignore_index=True)

    start_date = end_date - timedelta(days=lag)

    df_attendance = create_attendance_dataframe(data, start_date, end_date)

    df_attendance["day"] = df_attendance["date"].dt.date
    df_attendance["weekday"] = df_attendance["date"].dt.weekday
    df_attendance = df_attendance[df_attendance["weekday"].isin(selected_weekdays)]
    df_unique = df_attendance.drop_duplicates(subset=["worker_id", "day"])

    attendance_counts = df_unique.groupby(["worker_id", "weekday"]).size()

    weekday_distribution = (
        pd.date_range(start=start_date, end=end_date)
        .to_series()
        .dt.weekday
        .value_counts()
        .to_dict()
    )

    attendance_profiles: Dict[float, List[float]] = {}

    for worker_id in df_unique["worker_id"].unique():
        profile = []
        for weekday in selected_weekdays:
            attended = attendance_counts.get((worker_id, weekday), 0)
            possible = weekday_distribution.get(weekday, 0)
            profile.append(round(attended / possible, 3) if possible > 0 else 0.0)
        attendance_profiles[worker_id] = profile

    return attendance_profiles


def load_attendances(
    data: Dataset,
    lag: int = 90
) -> Dict[int, List[str]]:
    """
    Loads actual attendance data for all users as date strings.

    Args:
        data (Dataset): The dataset containing booking data.
        lag: Number of past days to include.

    Returns:
        Dictionary with user IDs as keys and list of attendance dates (YYYY-MM-DD) as values.
    """
    data["blockedFrom"] = pd.to_datetime(data["blockedFrom"], errors="coerce")

    variable = data[data["variableBooking"] == 1].copy()
    end_date = variable["blockedFrom"].max().date()

    data["blockedUntil"] = data["blockedUntil"].astype(str)
    data.loc[data["blockedUntil"] == "unlimited", "blockedUntil"] = pd.Timestamp(end_date)
    data["blockedUntil"] = pd.to_datetime(data["blockedUntil"], errors="coerce")

    fixed = data[data["variableBooking"] == 0].copy()
    fixed_expanded = expand_fixed_bookings(fixed)

    start_date = end_date - timedelta(days=lag)

    data = pd.concat([fixed_expanded, variable], ignore_index=True)

    df_attendance = create_attendance_dataframe(data, start_date, end_date)

    df_attendance = df_attendance.drop_duplicates()

    attendance_dict: Dict[int, List[str]] = {}
    for worker_id, group in df_attendance.groupby("worker_id"):
        attendance_dict[worker_id] = group["date"].tolist()

    return attendance_dict


def average_simulated_weeks(
    weeks: List[List[str]],
    weekdays: List[str] = ["Mo", "Di", "Mi", "Do", "Fr"] # FIXME: Change to English
) -> List[float]:
    """
    Calculates the average attendance percentage for each weekday based on simulated weeks.

    Args:
        weeks: A list of weeks, each week is a list of weekday abbreviations (e.g., 'Mo', 'Di', ...).
        weekdays: Used days of the week

    Returns:
        A list of attendance percentages (as floats) for each weekday from Monday to Sunday,
        in the order ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'].
    """
    all_days = [day for sublist in weeks for day in sublist]
    counter = Counter(all_days)
    total = len(weeks)
    percentages: Dict[str, float] = {day: count / total for day, count in counter.items()}
    percentages_sorted = {day: percentages.get(day, 0.0) for day in weekdays}
    return list(percentages_sorted.values())


def draw_days(
    attendance: Dict[float,List[float]],
    timeframe: str = "week",
    fixed_days: Optional[List[str]] = None,
    choseable_days: Optional[List[str]] = None,
    number_choseable_days: Optional[int] = None,
    number_days: Optional[int] = None,
    more_days_allowed: bool = True,
    weekdays: List[str] = ["Mo", "Di", "Mi", "Do", "Fr"] # FIXME: Change to English
) -> List[str]:
    """
    Generates a simulated week of attendance days based on the given policy configuration.

    Args:
        attendance: Attendance probabilities for weekdays (Mon-Sun).
        timeframe: Policy timeframe (currently only "week" is supported).
        fixed_days: Days that are always selected.
        choseable_days: Days from which a fixed number is chosen.
        number_choseable_days: Number of days to pick from `choseable_days`.
        number_days: Target total number of days.
        more_days_allowed: If True, adds additional days based on attendance.

    Returns:
        List[str]: List of weekday abbreviations representing the selected attendance days.
    """
    if timeframe != "week":
        raise ValueError("Only 'week' timeframe is supported.")

    days = fixed_days.copy() if fixed_days else []

    if choseable_days and number_choseable_days:
        available_days = [d for d in choseable_days if d not in days]
        choseable_days_left = number_choseable_days - sum(1 for d in days if d in choseable_days)

        if len(available_days) < choseable_days_left:
            raise ValueError(f"Not enough choseable days: need {choseable_days_left}, have {available_days}")
        if choseable_days_left > 0:
            days.extend(np.random.choice(available_days, choseable_days_left, replace=False))

    if number_days:
        if number_days < len(days):
            raise ValueError(f"Too many fixed/chosen days ({len(days)}) for target number_days={number_days}")
        num_draw = number_days - len(days)

        filtered_attendance = [
            -1 if weekdays[i] in days else prob
            for i, prob in enumerate(attendance)
        ]

        available = [weekdays[i] for i, prob in enumerate(filtered_attendance) if prob != -1]
        raw_probs = [prob + 0.1 for prob in filtered_attendance if prob != -1]
        prob_sum = sum(raw_probs)
        prob_values = [p / prob_sum for p in raw_probs]

        additional_days = list(np.random.choice(available, num_draw, replace=False, p=prob_values))
        days.extend(additional_days)

    if more_days_allowed:
        for i, day in enumerate(weekdays):
            if day not in days and np.random.rand() < attendance[i]:
                days.append(day)

    return sorted(days, key=weekdays.index)


#### TEST #################################################################################################################################################################################

if __name__ == "__main__":
    from pprint import pprint
    from deskquery.data.dataset import create_dataset

    dataset = create_dataset()

    ########## Test simulate_policy ################################################
    policy = {
        "fixed_days":["Di"],
        "choseable_days":["Mi", "Do"],
        "number_choseable_days":1,
        "number_days":3,
        "more_days_allowed":True
    }

    exceptions = {
        4: {'fixed_days': ["Fr"], 'number_days': 4, 'more_days_allowed': True},
        14: {'fixed_days': ["Fr"], 'number_days': 4, 'more_days_allowed': True}
    }

    random_assignments = [
        (10, {'number_days': 1, 'more_days_allowed': False})
    ]

    print("=== Simulate policy ===")
    return_dict = simulate_policy(
        data=dataset,
        policy=policy,
        exceptions=exceptions,
        random_assignments=random_assignments
    )
    pprint(return_dict["data"])
    print()

    ########## Test detect_policy_violations by worker ################################################
    print("=== Detect policy violations per worker ===")
    return_dict = detect_policy_violations(
        data=dataset,
        policy=policy,
        exceptions=exceptions,
        random_assignments=random_assignments
    )
    pprint(return_dict["data"])
    print()

    ########## Test detect_policy_violations in total ################################################
    print("=== Detect policy violations per worker ===")
    return_dict = detect_policy_violations(
        data=dataset,
        policy=policy,
        exceptions=exceptions,
        random_assignments=random_assignments,
        only_stats=True
    )
    pprint(return_dict["data"])
    print()

    ########## Test suggest_balanced_utilization_policy ################################################
    print("=== Suggest balanced utilization policy ===")
    # FIXME: This function is not defined!
    return_dict = suggest_balanced_utilization_policy(
        data=dataset,
        target_utilization=0.8
    )
    pprint(return_dict["data"])
    print()
