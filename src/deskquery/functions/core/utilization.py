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
) -> tuple[dict[str, float], int]:
    """
    Calculates the average utilization by desk, room, or weekday over a specified timeframe.

    The function always returns:
        - A dictionary of utilization values per aggregation key
        - An integer:
            - If `threshold` is set: the number of keys whose utilization is either
              above or below the threshold (depending on `count_below`)
            - If no `threshold` is set: the total number of keys in the result

    Args:
        data: Booking dataset (Dataset object).
        include_fixed: If True, expands fixed bookings into individual business days.
        by_desks: If True, aggregates utilization per desk (formatted as 'RoomName_DeskNumber').
        by_room: If True, aggregates utilization per room.
        by_day: If True, aggregates utilization per weekday name (e.g. 'Monday').
        desk_id: Optional desk filter before aggregation.
        room_name: Optional room filter before aggregation.
        weekday: List of weekday names to include (e.g. ['monday', 'wednesday']).
        start_date: Start of the analysis period. Defaults to 90 days ago.
        end_date: End of the analysis period. Defaults to today.
        threshold: If set, returns count of keys above or below this threshold.
        count_below: If True, counts keys with utilization below the threshold.
                     If False, counts keys with utilization greater than or equal to the threshold.

    Returns:
        tuple:
            - dict[str, float]: Mapping of aggregation key (room, desk, or weekday) to utilization (0.0–1.0)
            - int:
                - If `threshold` is set: number of keys above/below the threshold
                - If `threshold` is None: total number of keys in the utilization dictionary

    Raises:
        ValueError: If not exactly one of by_room, by_desks, or by_day is set to True.

    Examples:
        >>> analyze_utilization(data, by_room=True)
        ({'Room A': 0.78, 'Room B': 0.64}, 2)

        >>> analyze_utilization(data, by_day=True, threshold=0.7)
        ({'Monday': 0.82, 'Tuesday': 0.65}, 1)

        >>> analyze_utilization(data, by_desks=True, threshold=0.6, count_below=True)
        ({'Room A_1': 0.75, 'Room A_2': 0.55}, 1)
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
        total_possible_bookings = n_desks_per_room * count_matching_weekdays(start_date, end_date, weekday)      # here it should be num desks in room times time period
        actual_counts = key.value_counts()
        utilization = (actual_counts / total_possible_bookings).round(3)

    elif by_desks:
        key = df["roomName"] + "_" + df["deskNumber"].astype(str)
        total_possible_bookings = count_matching_weekdays(start_date, end_date, weekday)    # here the max utilaization is the nummber of days for every desk 
        actual_counts = key.value_counts()
        utilization = (actual_counts / total_possible_bookings).round(3)
    
    elif by_day:
        df["day"] = pd.to_datetime(df["blockedFrom"]).dt.day_name()
        key = df["day"]
        total_possible_bookings = data.get_n_desks()    # here the max utilaization is the nummber of desks for every day
        actual_counts = key.value_counts()
        utilization = (actual_counts / total_possible_bookings).round(3)
    
    else:
        raise ValueError("Invalid aggregation selection.")


    if threshold is not None:
        if count_below:
            return {key: value for key, value in utilization.to_dict().items() if value < threshold}, sum(1 for val in utilization.values if val < threshold)
        else:
            return {key: value for key, value in utilization.to_dict().items() if value >= threshold}, sum(1 for val in utilization.values if val >= threshold)
    
    return utilization.to_dict(), len(utilization)


def utilization_stats(
    data: Dataset,
    include_fixed: bool = False,
    
    by_desks: bool = False,
    by_room: bool = False,
    by_day: bool = False,

    desk_id: Optional[str] = None,
    room_name: Optional[str] = None,

    weekday: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict[str, dict[str, float]]:
    """
    Computes mean, min, max, and variance of utilization grouped by desk, room, or weekday.

    Args:
        data: Booking dataset.
        include_fixed: If True, expands fixed bookings into individual business days.
        by_desks: If True, compute stats per desk (formatted as Room_Desk).
        by_room: If True, compute stats per room.
        by_day: If True, compute stats per weekday.
        desk_id: Optional desk filter before aggregation.
        room_name: Optional room filter before aggregation.
        weekday: List of weekday names to include (e.g. ['monday', 'tuesday']).
        start_date: Start of analysis period. Defaults to 90 days ago.
        end_date: End of analysis period. Defaults to today.

    Returns:
        A dict mapping each key (e.g. 'Room A', 'Room_A_1', or 'Monday') to:
        {
            "mean": float,
            "min": float,
            "max": float,
            "var": float
        }

    Raises:
        ValueError: If not exactly one of by_room, by_desks, or by_day is set to True.
    """

    if sum([by_room, by_desks, by_day]) != 1:
        raise ValueError("You must set exactly one of by_room, by_desks, or by_day to True.")

    if start_date is None:
        start_date = datetime.today() - timedelta(days=90)
    if end_date is None:
        end_date = datetime.today()

    df = prepare_utilization_dataframe(data, include_fixed, desk_id, room_name, weekday, start_date, end_date)

    if by_room:
        key = df["roomName"]   
        total_possible_bookings = key.value_counts()                   # TODO handel this here          # here it should be num desks in room times time period?
    elif by_desks:
        key = df["roomName"] + "_" + df["deskNumber"].astype(str)
        total_possible_bookings = count_matching_weekdays(start_date, end_date, weekday)                # here the max utilaization is the nummber of days for every desk 
    elif by_day:
        df["day"] = pd.to_datetime(df["blockedFrom"]).dt.day_name()
        key = df["day"]
        total_possible_bookings = df.groupby("day")["deskNumber"].nunique()                              # here the max utilaization is the nummber of desks for every day
    else:
        raise ValueError("Invalid aggregation selection.")

    
    grouped = df.groupby(group_cols).size().unstack(fill_value=0)   # Count bookings per group

    stats = grouped.T.agg(["mean", "min", "max", "var"], axis=1).round(3)    # Transpose to have keys as rows compute stats across days

    return {
        k: {
            "mean": v["mean"],
            "min": v["min"],
            "max": v["max"],
            "var": v["var"]
        } for k, v in stats.iterrows()
    }





def detect_utilization_anomalies(
    data: Dataset,
    threshold: float = 0.2, 
    by_room: bool = False, 
    include_fixed: bool = False,
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> dict[str, float]:
    """
    Detects days or rooms with significant utilization anomalies.

    Args:
        data: Dataset to evaluate.
        threshold: Minimum absolute deviation from global mean to be flagged.
        by_room: If True, checks per room. If False, checks per weekday.
        include_fixed: Whether to expand fixed bookings.
        staThinking ...rt_date: Analysis start. Defaults to 90 days ago.
        end_date: Analysis end. Defaults to today.

    Returns:
        Dictionary of keys (room names or weekdays) with anomalous utilization values.
    """
    util = analyze_utilization(
        data=data,
        by_room=by_room,
        by_desks=False,
        by_day=not by_room,
        include_fixed=include_fixed,
        start_date=start_date,
        end_date=end_date,
    )

    if isinstance(util, tuple):  # safeguard if analyze_utilization returns tuple
        util = util[0]

    mean_util = sum(util.values()) / len(util)
    return {
        k: v for k, v in util.items()
        if abs(v - mean_util) >= threshold
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
        df: Filtered and preprocessed DataFrame
    """
    if start_date is None or end_date is None:
       raise ValueError("please Provide start and end data")
    
    if start_date > end_date:
        raise ValueError("Start date should be before end date")
     
    if room_name:
        data = data.get_rooms(room_name)
        print("yes")
    if desk_id:
        print("yes")
        data = data.get_desks(desk_id)
    if weekday:
        print("yes")
        data = data.get_days(weekday)

    df = data.get_timeframe(start_date=start_date, end_date=end_date).to_df()

    if include_fixed:
        df = df.replace("unlimited", end_date)
        df = expand_fixed_bookings(df, weekday=weekday)
    else:
        df = df[df["variableBooking"] == 1]

    df["day"] = pd.to_datetime(df["blockedFrom"]).dt.day_name()

    return df


def count_matching_weekdays(start_date, end_date, allowed_days):
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


#### TEST #################################################################################################################################################################################

if __name__ == "__main__":
    from pprint import pprint
    from deskquery.data.dataset import create_dataset

    dataset = create_dataset()

    start = datetime(2023, 1, 1)
    end = datetime(2025, 1, 1)

    
    df = dataset.get_timeframe(start_date=start, end_date=end).to_df()

    print(df[df["variableBooking"] == 0])


    print("=== Utilization by room ===")
    util_room, count_room = analyze_utilization(
        data=dataset,
        by_room=True,
        include_fixed=True,
        start_date=start,
        end_date=end
    )
    pprint(util_room)
    print("Num rooms:", count_room)
    print()

    print("=== Utilization by desk with threshold < 0.6 ===")
    util_desk, count_below = analyze_utilization(
        data=dataset,
        by_desks=True,
        include_fixed=True,
        start_date=start,
        end_date=end,
        threshold=0.6,
        count_below=True
    )
    pprint(util_desk)
    print("Desks under 60% Utalization:", count_below)
    print()

   
    print("=== Utilization by desk with threshold > 0.6 ===")
    util_desk, count_below = analyze_utilization(
        data=dataset,
        by_desks=True,
        include_fixed=True,
        start_date=start,
        end_date=end,
        threshold=0.6,
        count_below=False
    )
    pprint(util_desk)
    print("Desks over 60% Utalization:", count_below)
    print()

    print("=== Utilization by weekday for monday and friday ===")
    util_day, count_day = analyze_utilization(
        data=dataset,
        by_day=True,
        weekday=["monday", "friday"],
        include_fixed=True,
        start_date=start,
        end_date=end
    )
    pprint(util_day)
    
