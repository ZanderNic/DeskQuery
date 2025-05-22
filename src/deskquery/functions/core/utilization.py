# std-lib import
from typing import Optional, List
from datetime import datetime, timedelta

# third party imports
import pandas as pd

# project imports
from deskquery.data.dataset import Dataset


def analyze_utilization(
    data: Dataset,
    include_fixed: bool = False,
    
    by_desks: bool = False,
    by_room: bool = False,
    by_day: bool = False,
    
    desk_id: Optional[str] = None,
    room_name: Optional[str] = None,
    
    weekday: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,

    threshold: Optional[float] = None,
    count_below: bool = False,
) -> dict[str, object]:
    """
    Computes statistical measures of workspace utilization over time, grouped by desk, room, or weekday.

    Utilization is calculated by dividing the number of actual bookings by the number of possible bookings 
    per group (based on date range, included weekdays, and number of desks). Daily booking counts are used 
    to compute variability (min, max, variance) per group key.

    Args:
        data (Dataset): The dataset containing all bookings.
        include_fixed (bool): If True, expands recurring bookings across valid weekdays.
        by_desks (bool): If True, groups statistics by desk (e.g., 'Room_3').
        by_room (bool): If True, groups statistics by room.
        by_day (bool): If True, groups statistics by weekday (e.g., 'Monday').
        desk_id (Optional[List[int]]): If provided, filters the analysis to the selected desk IDs.
        room_name (Optional[List[str]]): If provided, filters the analysis to the selected rooms.
        weekday (List[str]): List of weekday names (e.g., ['monday', 'friday']) to include. Defaults to weekdays (Mon–Fri).
        start_date (Optional[datetime]): Start of the evaluation period. Defaults to 90 days ago.
        end_date (Optional[datetime]): End of the evaluation period. Defaults to today.

    Returns:
        dict: A structured result containing:
            - "data": dict[str, dict[str, float]]
                Mapping from group key to:
                {
                    "mean": Average utilization over time,
                    "min": Lowest daily utilization,
                    "max": Highest daily utilization,
                    "var": Variance of daily utilization
                }
            - "error": int
                0 if successful
            - "error_msg": str
                Empty string if no error
            - "plotable": int
                Placeholder for visualization integration (always 0)

    Raises:
        ValueError: If none or more than one of `by_desks`, `by_room`, or `by_day` is set to True.

    Example:
        >>> utilization_stats(data, by_room=True, include_fixed=True)
        {
            "data": {
                "Room A": {"mean": 0.63, "min": 0.4, "max": 0.9, "var": 0.02},
                "Room B": {"mean": 0.12, "min": 0.0, "max": 0.3, "var": 0.01}
            },
            "error": 0,
            "error_msg": "",
            "plotable": 0
        }
    """

    if sum([by_room, by_desks, by_day]) != 1:
        raise ValueError("You must set exactly one of by_room, by_desks, or by_day to True.")

    if start_date is None:
        start_date = datetime.today() - timedelta(days=90)
    if end_date is None:
        end_date = datetime.today()
    
    df = prepare_utilization_dataframe(data, include_fixed, desk_id, room_name, weekday, start_date, end_date)

    # Aggregation Key
    if by_room:                                                
        key = df["roomName"]
        n_desks_per_room = data.get_n_desks_per_room()
        total_possible =  n_desks_per_room * count_matching_weekdays(start_date, end_date, weekday)      # here it should be num desks in room times time period
        actual_counts = key.value_counts()
    
        utilization = pd.Series({
            room: round(actual_counts.get(room, 0) / total_possible.get(room, 1), 3)
            for room in total_possible.keys()
        })
        
    elif by_desks:
        key = df["roomName"] + "_" + df["deskNumber"].astype(str)   
        desk_keys = key.unique()
        total_possible = count_matching_weekdays(start_date, end_date, weekday)     # here the max utilaization is the nummber of days for every desk 
        
        actual_counts = key.value_counts()
        utilization = pd.Series({
            desk: round(actual_counts.get(desk, 0) / total_possible, 3)
            for desk in desk_keys
        })

    elif by_day:
        df["day"] = pd.to_datetime(df["blockedFrom"]).dt.day_name()
        key = df["day"]

        weekday_counts = count_weekday_occurrences(start_date, end_date, weekday or [])     # count the nummber of apperences od different days 
        n_desks = data.get_n_desks()
        total_possible = {day: count * n_desks for day, count in weekday_counts.items()}   # here the nummber of possible bookings is the nummber of apperances of the different weekday * the total nummber of desks that are available (the same for every day)
        actual_counts = key.value_counts()

        utilization = pd.Series({
            day: round(actual_counts.get(day, 0) / total_possible.get(day, 1), 3)
            for day in total_possible
        })
    else:
        raise ValueError("Invalid aggregation selection.")

    if threshold is not None:
        if count_below:
            utilization = utilization[utilization < threshold]
        else:
            utilization = utilization[utilization >= threshold]
            
    return {
        "data": {
            "utilization": utilization.to_dict(), 
            "count": len(utilization)
        },
        "error":  0,
        "error_msg": "",
        "plotable": True
    }


def utilization_stats(
    data: Dataset,
    include_fixed: bool = False,
    
    by_desks: bool = False,
    by_room: bool = False,
    by_day: bool = False,
    
    desk_id: Optional[List[int]] = None,
    room_name: Optional[List[str]] = None,
    weekday: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"],
    
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict[str, object]:
    """
    Identifies utilization outliers based on deviation from the global mean.

    This function detects keys (desks, rooms, or weekdays) whose average utilization deviates significantly 
    from the global mean (by at least the given threshold). It uses the same aggregation logic as 
    `analyze_utilization` and returns only the outlier entries.

    Args:
        data (Dataset): The dataset containing booking data.
        include_fixed (bool): If True, expands recurring bookings into daily entries.
        threshold (float): Minimum absolute deviation from the mean to classify as anomalous.
        by_desks (bool): If True, detects anomalies per desk.
        by_room (bool): If True, detects anomalies per room.
        by_day (bool): If True, detects anomalies per weekday.
        desk_id (Optional[List[int]]): Optional desk filter.
        room_name (Optional[List[str]]): Optional room filter.
        weekday (List[str]): List of weekdays to consider in the analysis.
        start_date (Optional[datetime]): Start of the analysis window. Defaults to 90 days ago.
        end_date (Optional[datetime]): End of the analysis window. Defaults to today.

    Returns:
        dict: A dictionary containing:
            - "data": dict[str, float]
                Keys with anomalous utilization values (deviation ≥ threshold).
            - "count": int
                Number of detected anomalies.
            - "error": int
                0 if successful.
            - "error_msg": str
                Empty if no error.
            - "plotable": bool
                Always True (can be visualized directly)

    Raises:
        ValueError: If none or more than one of `by_desks`, `by_room`, or `by_day` is set to True.

    Example:
        >>> detect_utilization_anomalies(data, by_day=True, threshold=0.1)
        {
            "data": {
                "Monday": 0.71,
                "Friday": 0.39
            },
            "count": 2,
            "error": 0,
            "error_msg": "",
            "plotable": True
        }
    """


    if sum([by_room, by_desks, by_day]) != 1:
        raise ValueError("You must set exactly one of by_room, by_desks, or by_day to True.")

    if start_date is None:
        start_date = datetime.today() - timedelta(days=90)
    if end_date is None:
        end_date = datetime.today()

    df = prepare_utilization_dataframe(data, include_fixed, desk_id, room_name, weekday, start_date, end_date)

    if by_room:
        df["key"] = df["roomName"]
        total_possible = data.get_n_desks_per_room() * count_matching_weekdays(start_date, end_date, weekday)      #  if by room the max possible boockings are desks_per_room
    
    elif by_desks:
        df["key"] = df["roomName"] + "_" + df["deskNumber"].astype(str)
        total_possible = count_matching_weekdays(start_date, end_date, weekday)     # here the max utilaization is the nummber of days for every desk 
        
    elif by_day:
        df["key"] = df["day"]    
        weekday_counts = count_weekday_occurrences(start_date, end_date, weekday or [])         # count the nummber of apperences od different days 
        n_desks = data.get_n_desks()
        total_possible = {day: count * n_desks for day, count in weekday_counts.items()}        # here the nummber of possible bookings is the nummber of apperances of the different weekday * the total nummber of desks that are available (the same for every day)
    
    grouped = df.groupby(["key", "blockedFrom"]).size()                                         # create a grouped df by key and day 
    stats = grouped.groupby("key").agg(sum="sum", min="min", max="max")                         # group again by the key and get the sum, min, max per bocked day (blockedFrom) 
    stats["sumsq"] = grouped.groupby("key").apply(lambda x: (x**2).sum()).round(3)              # to callcualte the var later
    
    result_data_dict = {}
  
    for key, values in stats.iterrows():
        max_possible = total_possible.get(key, 1)                                       # scale the sum with the max_possible to get the mean 
        mean = float(round(values["sum"] / max_possible, 3))
        result_data_dict[key] = {                                               
            "mean": mean,
            "min": float(round(values["min"] / max_possible, 3)),
            "max": float(round(values["max"] / max_possible, 3)),                       # scale the min, max with max possible to get the utilization
            "var": float(round(values["sumsq"] / max_possible - (mean) ** 2, 6)),       # use the mean and the sumsq to callculate the var
        }

    return {
        "data": result_data_dict,
        "error": 0,
        "plotable": 0,
        "error_msg": ""
    }


def detect_utilization_anomalies(
    data: Dataset,
    include_fixed: bool = False,
    
    threshold: float = 0.2, 
    
    by_desks: bool = False,
    by_room: bool = False,
    by_day: bool = False,
    
    desk_id: Optional[List[int]] = None,
    room_name: Optional[List[str]] = None,
    weekday: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"],
    
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict[str, object]:
    """
    Detects rooms or weekdays with anomalously high or low utilization values.

    Args:
        data (Dataset): Booking dataset.
        threshold (float): Minimum absolute deviation from the global mean utilization.
        by_room (bool): If True, analyze by room. If False, analyze by weekday.
        include_fixed (bool): Whether to include expanded fixed bookings.
        start_date (datetime, optional): Start date for analysis.
        end_date (datetime, optional): End date for analysis.

    Returns:
        dict: Structure:
            {
                "data": {key: utilization_value},
                "count": int,
                "error": 0,
                "error_msg": str,
                "plotable": True
            }
    """
    result = analyze_utilization(
        data = data,
        include_fixed=include_fixed,
         
        by_room = by_room,
        by_desks = by_desks,
        by_day = by_day,
        
        desk_id = desk_id,
        room_name = room_name,
        weekday = weekday,
        
        start_date=start_date,
        end_date=end_date,
    )

    utilization = result["data"]["utilization"]
    
    mean_util = sum(utilization.values()) / (len(utilization))
    
    anomalies = {
        key: value for key, value in utilization.items()
        if abs(value - mean_util) >= threshold
    }

    return {
        "data": anomalies,
        "count": len(anomalies),
        "error": 0,
        "error_msg": "",
        "plotable": True
    }



####### Helpers ########################################################################################################################################################################### 


def expand_fixed_bookings(data, start_col="blockedFrom", end_col="blockedUntil", weekday: list[str] = None):
    """
    Expands fixed bookings over all business days between start and end dates,
    optionally filtering by allowed weekdays.

    Args:
        data (pd.DataFrame): Input bookings.
        start_col (str): Column with booking start date.
        end_col (str): Column with booking end date.
        weekday (list[str], optional): List of allowed weekdays (e.g. ['monday', 'wednesday']).

    Returns:
        pd.DataFrame: Expanded bookings filtered by weekday.
    """
    if weekday is None:
        weekday = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']

    weekday = [w.lower() for w in weekday]

    variable = data[data["variableBooking"] == 1]
    fixed = data[data["variableBooking"] == 0].copy()

    if fixed.empty:
        return variable

    fixed["workdays"] = fixed.apply(
        lambda row: pd.date_range(row[start_col], row[end_col], freq='B'),
        axis=1
    )

    fixed = fixed.explode("workdays")

    fixed = fixed[fixed["workdays"].dt.day_name().str.lower().isin(weekday)]

    fixed[start_col] = fixed["workdays"]
    fixed[end_col] = fixed["workdays"]
    fixed = fixed.drop(columns=["workdays"]).reset_index(drop=True)

    return pd.concat([fixed, variable], ignore_index=True)


def prepare_utilization_dataframe(
    data: Dataset,
    include_fixed: bool = False,
    desk_id: Optional[str] = None,
    room_name: Optional[str] = None,
    weekday: List[str] = None,
    start_date: datetime = None,
    end_date: datetime = None,
) -> pd.DataFrame:
    """
    Filters, expands, and prepares the booking DataFrame for utilization analysis.

    Args:
        data: The Dataset object.
        include_fixed: If True, expands fixed bookings into individual days.
        desk_id: Optional desk filter.
        room_name: Optional room filter.
        weekday: List of weekdays to include (e.g. ["monday", "wednesday"]).
        start_date: Start of timeframe. Defaults to 90 days ago.
        end_date: End of timeframe. Defaults to today.

    Returns:
        pd.DataFrame: Filtered and preprocessed DataFrame ready for aggregation.
    """
    if start_date is None or end_date is None:
       raise ValueError("please Provide start and end data")
    
    if start_date > end_date:
        raise ValueError("Start date should be before end date")
     
    if room_name:
        data = data.get_rooms(room_name)
    if desk_id:
        data = data.get_desks(desk_id)
    if weekday:
        data = data.get_days(weekday)

    df = data.get_timeframe(start_date=start_date, end_date=end_date)

    if include_fixed:
        df = df.replace("unlimited", end_date)
        df = expand_fixed_bookings(df, weekday=weekday)
    else:
        df = df[df["variableBooking"] == 1]

    df["day"] = pd.to_datetime(df["blockedFrom"]).dt.day_name()

    return df


def count_matching_weekdays(start_date, end_date, allowed_days):
    """
    Counts the number of dates between start_date and end_date that fall on specified weekdays.

    Args:
        start_date (datetime): Start of the date range (inclusive).
        end_date (datetime): End of the date range (inclusive).
        allowed_days (list[str] or None): List of weekday names to count (e.g., ['monday', 'wednesday']).
                                        If None, defaults to all weekdays (Mon–Fri).

    Returns:
        int: Total number of days within the date range that match the specified weekdays.
    """
    
    if allowed_days is None:
        allowed_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        
    allowed_days = set(d.lower() for d in allowed_days)
    count = 0
    current = start_date

    while current <= end_date:
        if current.strftime('%A').lower() in allowed_days:
            count += 1
        current += timedelta(days=1)

    return count


def count_weekday_occurrences(start_date: datetime, end_date: datetime, allowed_days: List[str]) -> dict[str, int]:
    """
    Counts how many times each allowed weekday occurs between start_date and end_date.

    Returns:
        Dict mapping weekday name (e.g., 'Monday') to number of occurrences.
    """
    allowed_days_set = {d.lower() for d in allowed_days}
    counts = {day.capitalize(): 0 for day in allowed_days_set}

    current = start_date
    while current <= end_date:
        weekday = current.strftime('%A')
        if weekday.lower() in allowed_days_set:
            counts[weekday] += 1
        current += timedelta(days=1)
    
    return counts


#### TEST #################################################################################################################################################################################

if __name__ == "__main__":
    from pprint import pprint
    from deskquery.data.dataset import create_dataset

    dataset = create_dataset()

    start = datetime(2023, 1, 1)
    end = datetime(2025, 6, 1)


    ########## Test analyze_utilization ################################################

    print("=== Utilization by room ===")
    return_dict = analyze_utilization(
        data=dataset,
        by_room=True,
        include_fixed=True,
        start_date=start,
        end_date=end
    )
    pprint(return_dict["data"]["utilization"])
    print("Num rooms:", return_dict["data"]["count"])
    print()
   
    print("=== Utilization by desk with threshold > 0.6 ===")
    return_dict = analyze_utilization(
        data=dataset,
        by_desks=True,
        include_fixed=True,
        start_date=start,
        end_date=end,
        threshold=0.6,
        count_below=False
    )
    pprint(return_dict["data"]["utilization"])
    print("Desks over 60% Utalization:", return_dict["data"]["count"])
    print()

    print("=== Utilization by weekday for monday, tuesday, friday ===")
    return_dict = analyze_utilization(
        data=dataset,
        by_day=True,
        weekday=["monday", "tuesday", "friday"],
        include_fixed=True,
        start_date=start,
        end_date=end
    )
    
    pprint(return_dict["data"]["utilization"])
    print()
    
    
    ########## Test utilization_stats ################################################
    
    print("=== Room-wise Utilization Stats ===")
    return_dict = utilization_stats(
        data=dataset,
        by_room=True,
        include_fixed=True,
        start_date=start,
        end_date=end,
    )
    pprint(return_dict["data"])
    print()
    
    print("\n=== Weekday-wise Utilization Stats for monday, tuesday, friday ===")
    return_dict = utilization_stats(
        data=dataset,
        by_day=True,
        weekday=["monday", "tuesday", "friday"],
        include_fixed=True,
        start_date=start,
        end_date=end,
    )
    pprint(return_dict["data"])
    print()


    ########## Test detect_utilization_anomalies ################################################

    print("=== Anomaly detection by room ===")
    result = detect_utilization_anomalies(
        data=dataset,
        by_room=True,
        threshold=0.1,
        include_fixed=True,
        start_date=start,
        end_date=end
    )
    pprint(result["data"])
    print("Count:", result["count"])
    print()

    print("=== Anomaly detection by weekday ===")
    result = detect_utilization_anomalies(
        data=dataset,
        by_day=True,
        threshold=0.02,
        include_fixed=True,
        start_date=start,
        end_date=end
    )
    pprint(result["data"])
    print("Count:", result["count"])
    print()
