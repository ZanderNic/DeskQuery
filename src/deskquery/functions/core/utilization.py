# std-lib import
from typing import Optional, List, Dict
import datetime
from datetime import timedelta

# third party imports
from numpy import right_shift
import pandas as pd

# project imports
from deskquery.data.dataset import Dataset
from deskquery.functions.types import PlotForFunction, FunctionRegistryExpectedFormat
from deskquery.functions.core.helper.plot_helper import *


def mean_utilization(
    data: Dataset,
    include_fixed: Optional[bool] = False,
    by_desks: bool = False,
    by_room: bool = False,
    by_day: bool = False,
    desk_id: Optional[List[int]] = None,
    room_name: Optional[List[str]] = None,
    weekday: Optional[List[str]] = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    threshold: Optional[float] = None,
    top_or_bottom_n: Optional[int] = None,
    from_bottom: Optional[bool] = False,
) -> FunctionRegistryExpectedFormat:
    """
    Computes mean utilization of workspace utilization over a given timeframe, grouped by either desk, room, or weekday.
    Should only be used to group by one of those attributes.

    Utilization is defined as the number of actual bookings divided by the number of possible bookings per group.
    The possible bookings depend on the time window, included weekdays, selected desk_ids or selected room_names.

    Optionally, the result can be filtered by a threshold or by selecting only the top or bottom N utilization values by 
    providing a threshold and selecting with from_bottom = True all entities where utilization <= threshold or with
    False utilization >= threshold. The same goes with the top_or_bottom_n where from_bottom = False means the top N
    utilizations and with from_bottom = True the bottom N utilizations.

    Args:
        data (Dataset):
            The dataset containing all bookings.
        include_fixed (bool, optional): 
            If True, expands recurring (fixed) bookings across valid weekdays. Defaults to False.
        by_desks (bool):
            If True, groups statistics by individual desk (e.g., 'Room_3'). Defaults to False.
        by_room (bool): 
            If True, groups statistics by room. Defaults to False.
        by_day (bool): 
            If True, groups statistics by weekday name (e.g., 'Monday'). Defaults to False.
        desk_id (List[int], optional):
            If provided, filters the analysis to the selected desk IDs.
            Defaults to `None`, meaning no filtering is applied.
        room_name (List[str], optional):
            If provided, filters the analysis to the selected room names.
            Defaults to `None`, meaning no filtering is applied.
        weekday (List[str], optional):
            List of weekday names (e.g., ['monday', 'friday']) to include in analysis.
            If `None`, defaults to all weekdays (Monday to Friday).
        start_date (datetime.datetime, optional): 
            Start of the evaluation period. If `None`, defaults to 90 days ago.
        end_date (datetime.datetime, optional): 
            End of the evaluation period. If `None`, defaults to today.
        threshold (float, optional):
            Optional minimum or maximum utilization threshold to filter results where min
            or max is selected by the bottom bool. Defaults to `None`, meaning no filtering is applied.
        top_or_bottom_n (int, optional): 
            Returns only the top or bottom N utilization entries. Defaults to `None`, meaning no filtering is applied.
        from_bottom (Optional[bool]):
            Direction of the `top_or_bottom_n` filter. Defaults to False.
            If True, selects the lowest N or utilization <= threshold (bottom performers).
            If False, selects the highest N or utilization >= threshold (top performers).

    Raises:
        ValueError:
            If none or more than one of `by_desks`, `by_room`, or `by_day` is set to True.

    Returns:
        FunctionRegistryExpectedFormat:
            Contains the data and plots of the grouped mean workspace utilization.
    """
    if sum([by_room, by_desks, by_day]) != 1:
        raise ValueError("You must set exactly one of by_room, by_desks, or by_day to True.")

    # set default values if applicable
    if include_fixed is None:
        include_fixed = False
    if not weekday:
        weekday = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
    elif isinstance(weekday, str):
        weekday = [weekday.lower()]
    if not start_date:
        start_date = datetime.datetime.today() - timedelta(days=90)
    if not end_date:
        end_date = datetime.datetime.today()
    if from_bottom is None:
        from_bottom = False
    
    df = prepare_utilization_dataset(
        data=data,
        start_date=start_date,
        end_date=end_date,
        include_fixed=include_fixed,
        desk_id=desk_id,
        room_name=room_name,
        weekday=weekday
    )

    # aggregation key
    if by_room:                                                
        key = df["roomName"]
        n_desks_per_room = data.get_desks_per_room_count()
       
        total_possible = n_desks_per_room * count_matching_weekdays(start_date, end_date, weekday)       # here it should be num desks in room times time period
        actual_counts = key.value_counts()
        column_name = "room"

        utilization = pd.Series({
            room: round(actual_counts.get(room, 0) / total_possible.get(room, 1), 3)
            for room in total_possible.keys()
        })
        
    elif by_desks:
        key = df["roomName"] + "_" + df["deskNumber"].astype(str)   
        df["composite_key"] = key
        desk_keys = key.unique()
         
        total_possible = count_matching_weekdays(start_date, end_date, weekday)       # here the max utilization is the number of days for every desk
        column_name = "desk"
        
        actual_counts = key.value_counts()
        utilization = pd.Series({
            desk: round(actual_counts.get(desk, 0) / total_possible, 3)
            for desk in desk_keys
        })
        
        desk_key_to_id = df.drop_duplicates("composite_key").set_index("composite_key")["deskId"].to_dict()

        desk_ids = {
            desk_key_to_id[key]: utilization[key]
            for key in utilization.index
            if key in desk_key_to_id
        }


    elif by_day:
        df["day"] = pd.to_datetime(df["blockedFrom"]).dt.day_name()
        key = df["day"]

        weekday_counts = count_weekday_occurrences(start_date, end_date, weekday)           # count the number of appearances of different days
        n_desks = data.get_desks_count()

        # here the number of possible bookings is the number of appearances of the different
        # weekday * the total number of desks that are available (the same for every day)
        total_possible = {day: count * n_desks for day, count in weekday_counts.items()}
        actual_counts = key.value_counts()
        column_name = "day"

        utilization = pd.Series({
            day: round(actual_counts.get(day, 0) / total_possible.get(day, 1), 3)
            for day in total_possible
        })
    else:
        raise ValueError("Invalid aggregation selection.")

    if threshold:
        if from_bottom:
            utilization = utilization[utilization <= threshold]
        else:
            utilization = utilization[utilization >= threshold]
        
    if top_or_bottom_n:
        utilization = utilization.sort_values(ascending=from_bottom)[:top_or_bottom_n]
    
    data_return = utilization.to_dict()
    
    # change the plot type depending on for what we have the utilization
    if by_room:  
        plot = PlotForFunction(
            default_plot=generate_map(
                room_names= data_return,
                title="Utalization in the different rooms in %",
                label_markings="utalization"
            ),
            available_plots=[generate_map]
        )
    elif by_day:
        plot = PlotForFunction(
            default_plot=generate_barchart(
                data={"Utilization": data_return},
                title=column_name,
                xaxis_title=column_name,
                yaxis_title="mean utilization in %"
            ),
            available_plots=[generate_barchart]
        )
    else:
        plot = PlotForFunction(
            default_plot=generate_map(
                desk_ids= desk_ids,
                title="Utalization of the different desks in %",
                label_markings="utalization"
            ),
            available_plots=[generate_map]
        )

    return FunctionRegistryExpectedFormat(
        data=data_return, 
        plot=plot
    )


def utilization_stats(
    data: Dataset,
    include_fixed: Optional[bool] = False,
    by_desks: bool = False,
    by_room: bool = False,
    by_day: bool = False,
    desk_id: Optional[List[int]] = None,
    room_name: Optional[List[str]] = None,
    weekday: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"],
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
) -> FunctionRegistryExpectedFormat:
    """
    Identifies utilization outliers based on deviation from the global mean.

    # FIXME: TO BE UPDATED
    This function detects keys (desks, rooms, or weekdays) whose average utilization deviates significantly 
    from the global mean (by at least the given threshold). It uses the same aggregation logic as 
    `analyze_utilization` and returns only the outlier entries.
    # FIXME: TO BE UPDATED

    Args:
        data (Dataset): 
            The dataset containing booking data.
        include_fixed (bool): 
            If True, expands recurring bookings into daily entries. Defaults to False.
        by_desks (bool):
            If True, groups statistics by individual desk (e.g., 'Room_3'). Defaults to False.
        by_room (bool): 
            If True, groups statistics by room. Defaults to False.
        by_day (bool): 
            If True, groups statistics by weekday name (e.g., 'Monday'). Defaults to False.
        desk_id (List[int], optional):
            If provided, filters the analysis to the selected desk IDs.
            Defaults to `None`, meaning no filtering is applied.
        room_name (List[str], optional):
            If provided, filters the analysis to the selected rooms.
            Defaults to `None`, meaning no filtering is applied.
        weekday (List[str], optional):
            List of weekday names (e.g., ['monday', 'friday']) to include in analysis.
            If `None`, defaults to all weekdays (Monday to Friday).
        start_date (datetime.datetime, optional): 
            Start of the evaluation period. If `None`, defaults to 90 days ago.
        end_date (datetime.datetime, optional): 
            End of the evaluation period. If `None`, defaults to today.

    Raises:
        ValueError:
            If none or more than one of `by_desks`, `by_room`, or `by_day` is set to True.

    Returns:
        FunctionRegistryExpectedFormat:
            Contains the data of identified utilization outliers.
    """
    if sum([by_room, by_desks, by_day]) != 1:
        raise ValueError("You must set exactly one of by_room, by_desks, or by_day to True.")

    # set default values if applicable
    if include_fixed is None:
        include_fixed = False
    if not weekday:
        weekday = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
    elif isinstance(weekday, str):
        weekday = [weekday.lower()]
    if not start_date:
        start_date = datetime.datetime.today() - timedelta(days=90)
    if not end_date:
        end_date = datetime.datetime.today()

    df = prepare_utilization_dataset(
        data=data,
        start_date=start_date,
        end_date=end_date,
        include_fixed=include_fixed,
        desk_id=desk_id,
        room_name=room_name,
        weekday=weekday
    )

    if by_room:
        df["key"] = df["roomName"]
        # if by room the max possible bookings are desks_per_room
        total_possible = data.get_desks_per_room_count() * count_matching_weekdays(start_date, end_date, weekday)

    elif by_desks:
        df["key"] = df["roomName"] + "_" + df["deskNumber"].astype(str)
        # here the max utilization is the number of days for every desk
        total_possible = count_matching_weekdays(start_date, end_date, weekday)

    elif by_day:
        df["key"] = df["day"]
        # count the number of appearances od different days
        weekday_counts = count_weekday_occurrences(start_date, end_date, weekday)
        n_desks = data.get_desks_count()
        # here the number of possible bookings is the number of appearances of the different
        # weekdays * the total number of desks that are available (the same for every day)
        total_possible = {day: count * n_desks for day, count in weekday_counts.items()}

    # create a grouped df by key and day
    grouped = df.groupby(["key", "blockedFrom"]).size()
    # group again by the key and get the sum, min, max per bocked day (blockedFrom)
    stats = grouped.groupby("key").agg(sum="sum", min="min", max="max")
    stats["sumsq"] = grouped.groupby("key").apply(lambda x: (x**2).sum()).round(3)  # to calculate the variance later

    result_data_dict = {}

    for key, values in stats.iterrows():
        # scale the sum with the max_possible to get the mean
        max_possible = total_possible.get(key, 1)
        mean = float(round(values["sum"] / max_possible, 3))
        result_data_dict[key] = {                                               
            "mean": mean,
            "min": float(round(values["min"] / max_possible, 3)),
            # scale the min, max with max possible to get the utilization
            "max": float(round(values["max"] / max_possible, 3)),
            # use the mean and the sumsq to calculate the variance
            "var": float(round(values["sumsq"] / max_possible - mean ** 2, 6)),
        }

    return FunctionRegistryExpectedFormat(
        data=result_data_dict, 
        plot=PlotForFunction()
    )


def detect_utilization_anomalies(
    data: Dataset,
    include_fixed: Optional[bool] = False,
    threshold: Optional[float] = 0.2,
    by_desks: bool = False,
    by_room: bool = False,
    by_day: bool = False,
    desk_id: Optional[List[int]] = None,
    room_name: Optional[List[str]] = None,
    weekday: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"],
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
) -> FunctionRegistryExpectedFormat:
    """
    Detects desks, rooms or weekdays with abnormally high or low mean utilization values.

    Args:
        data (Dataset): 
            The dataset containing booking data.
        threshold (float, optional): 
            Minimum absolute deviation from the global mean utilization. Defaults to 0.2.
        by_desks (bool):
            If True, groups statistics by individual desk (e.g., 'Room_3'). Defaults to False.
        by_room (bool): 
            If True, groups statistics by room. Defaults to False.
        by_day (bool): 
            If True, groups statistics by weekday name (e.g., 'Monday'). Defaults to False.
        desk_id (List[int], optional):
            If provided, filters the analysis to the selected desk IDs.
            Defaults to `None`, meaning no filtering is applied.
        room_name (List[str], optional):
            If provided, filters the analysis to the selected rooms.
            Defaults to `None`, meaning no filtering is applied.
        weekday (List[str], optional):
            List of weekday names (e.g., ['monday', 'friday']) to include in analysis.
            If `None`, defaults to all weekdays (Monday to Friday).
        start_date (datetime.datetime, optional): 
            Start of the evaluation period. If `None`, defaults to 90 days ago.
        end_date (datetime.datetime, optional): 
            End of the evaluation period. If `None`, defaults to today.

    Returns:
        FunctionRegistryExpectedFormat:
            Contains the data and plots of abnormal utilizations.
    """
    # set default values if applicable
    if threshold is None or not isinstance(threshold, (int, float)) or threshold < 0:
        threshold = 0.2

    result = mean_utilization(
        data=data,
        include_fixed=include_fixed,
        by_room=by_room,
        by_desks=by_desks,
        by_day=by_day,
        desk_id=desk_id,
        room_name=room_name,
        weekday=weekday,
        start_date=start_date,
        end_date=end_date,
    )

    utilization = result["data"]
    mean_util = sum(utilization.values()) / (len(utilization))

    anomalies = {
        key: value for key, value in utilization.items()
        if abs(value - mean_util) >= threshold
    }

    plot = PlotForFunction(
        default_plot=generate_barchart(
            data={"anomalies": anomalies},
            yaxis_title="mean utilization"
        ),
        available_plots=[generate_barchart]
    )

    return FunctionRegistryExpectedFormat(
        data=anomalies, 
        plot=plot
    )


####### Helpers ########################################################################################################

def expand_fixed_bookings(
    data,
    start_col="blockedFrom",
    end_col="blockedUntil",
    weekday: list[str] = None
):
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
    if not weekday:
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


def prepare_utilization_dataset(
    data: Dataset,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    include_fixed: bool = False,
    desk_id: Optional[List[int]] = None,
    room_name: Optional[List[str]] = None,
    weekday: Optional[List[str]] = None,
) -> Dataset:
    """
    Filters, expands, and prepares the booking Dataset for utilization analysis.

    Args:
        data (Dataset): The Dataset object.
        start_date (datetime.datetime): Start of timeframe. Defaults to 90 days ago.
        end_date (datetime.datetime): End of timeframe. Defaults to today.
        include_fixed (bool): If True, expands fixed bookings into individual days.
        desk_id (list[int], optional): Optional desk filter.
        room_name (list[str], optional): Optional room filter.
        weekday (list[str], optional): List of weekdays to include (e.g. ["monday", "wednesday"]).

    Returns:
        Dataset: Filtered and preprocessed Dataset ready for aggregation.
    """
    if start_date > end_date:
        raise ValueError("Start date should be before end date")
     
    if room_name:
        data = data.get_rooms(room_name)
    if desk_id:
        data = data.get_desks(desk_id)

    dataset = data.get_timeframe(start_date=start_date, end_date=end_date)

    if include_fixed:
        dataset = dataset.replace("unlimited", end_date)
        dataset = expand_fixed_bookings(dataset, weekday=weekday)
    else:
        dataset = dataset[dataset["variableBooking"] == 1]

    if weekday:
        dataset = dataset.get_days(weekday)

    dataset["day"] = pd.to_datetime(dataset["blockedFrom"]).dt.day_name()

    return dataset


def count_matching_weekdays(
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    allowed_days: Optional[List[str]] = None
) -> int:
    """
    Counts the number of dates between start_date and end_date that fall on specified weekdays.

    Args:
        start_date (datetime.datetime):
            Start of the date range (inclusive).
        end_date (datetime.datetime):
            End of the date range (inclusive).
        allowed_days (list[str] or None):
            List of weekday names to count (e.g., ['monday', 'wednesday']).
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


def count_weekday_occurrences(
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    allowed_days: List[str]
) -> Dict[str, int]:
    """
    Counts how many times each allowed weekday occurs between start_date and end_date.

    Args:
        start_date (datetime.datetime): Start of the date range (inclusive).
        end_date (datetime.datetime): End of the date range (inclusive).
        allowed_days (list[str]): List of weekday names to look for (e.g., ['tuesday', 'friday']).

    Returns:
        Dict[str, int]:
            A mapping of weekday names (e.g., 'Monday') to their number of occurrences.
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


#### TEST ##############################################################################################################

if __name__ == "__main__":
    from pprint import pprint
    from deskquery.data.dataset import create_dataset

    dataset = create_dataset()

    start = datetime.datetime(2023, 1, 1)
    end = datetime.datetime(2025, 6, 1)


    ########## Test mean_utilization ################################################

    print("=== Utilization by room ===")
    return_dict = mean_utilization(
        data=dataset,
        by_room=True,
        include_fixed=True,
        start_date=start,
        end_date=end
    )
    pprint(return_dict["data"])
    print("Num rooms:", len(return_dict["data"]))
    print()
   
    print("=== Utilization by desk with threshold > 0.6 ===")
    return_dict = mean_utilization(
        data=dataset,
        by_desks=True,
        include_fixed=True,
        start_date=start,
        end_date=end,
        threshold=0.6,
        from_bottom=False
    )
    pprint(return_dict["data"])
    print("Desks over 60% Utalization:", len(return_dict["data"]))
    print()
    
    
    print("=== Utilization by desk with top 5 desks ===")
    return_dict = mean_utilization(
        data=dataset,
        by_desks=True,
        include_fixed=True,
        start_date=start,
        end_date=end,
        top_or_bottom_n = 5,
        from_bottom = False
    )
    print("Top 5 Desks by Utalization:", return_dict["data"])
    print()


    print("=== Utilization by weekday for monday, tuesday, friday ===")
    return_dict = mean_utilization(
        data=dataset,
        by_day=True,
        weekday=["monday", "tuesday", "friday"],
        include_fixed=True,
        start_date=start,
        end_date=end
    )
    
    pprint(return_dict["data"])
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
    
    print("\n=== Weekday-wise Utilization Stats for monday, friday ===")
    return_dict = utilization_stats(
        data=dataset,
        by_day=True,
        weekday=["monday", "friday"],
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
    print(result["data"])
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
    print(result["data"])
    print()



    from deskquery.functions.core.plot import generate_plot_for_function

    print("=== Test: Plot mean_utilization (by_room) ===")
    return_dict = mean_utilization(
        data=dataset,
        by_room=True,
        include_fixed=True,
        start_date=start,
        end_date=end
    )
    print(return_dict["data"])
    plot_result = generate_plot_for_function(return_dict)
    plot_result.plot.default_plot.show() 
    

    print("=== Test: Plot mean_utilization (by_deks) ===")
    return_dict = mean_utilization(
        data=dataset,
        by_desks=True,
        threshold=0.02,
        include_fixed=True,
        start_date=start,
        end_date=end
    )
    plot_result = generate_plot_for_function(return_dict)
    plot_result.plot.default_plot.show() 