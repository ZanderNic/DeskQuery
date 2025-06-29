#!/usr/bin/env python 
from typing import Optional, List, Literal, Sequence, Dict
import datetime
import pandas as pd
from collections import Counter
from itertools import combinations
from deskquery.data.dataset import Dataset
from deskquery.functions.types import FunctionRegistryExpectedFormat, PlotForFunction
from deskquery.functions.core.helper.plot_helper import generate_barchart

def get_avg_employee_bookings(
    data: Dataset,
    user_names: Optional[str | Sequence[str]] = None,
    user_ids: Optional[int | Sequence[int]] = None,
    num_employees: Optional[int] = None,
    return_total_mean: Optional[bool] = False,
    granularity: Literal["day", "week", "month", "year"] = 'year',
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"],
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    include_double_bookings: Optional[bool] = False,
    include_fixed: Optional[bool] = True,
    return_user_names: Optional[bool] = True,
    include_non_booking_users: Optional[bool] = False
) -> FunctionRegistryExpectedFormat:
    """
    Compute average booking frequency per employee over a specified time granularity.

    Parameters:
        data (Dataset):
            Dataset with booking information.
        user_names (str | Sequence[str], optional): 
            Filter for specific usernames. Defaults to `None`, which means no filtering is applied.
        user_ids (int | Sequence[int], optional): 
            Filter for specific user IDs. Defaults to `None`, which means no filtering is applied.
        num_employees (int, optional): 
            Limit result to top-N employees by average bookings. Defaults to `None`, which means all employees are included.
        return_total_mean (bool, optional): 
            If True, return the mean over all employees instead of per-user values. Defaults to False.
        granularity (str):
            Time unit for averaging. One of "day", "week", "month", or "year". Default is "year".
        weekdays (List[str]):
            Days of the week to include in the analysis. Defaults to `None`, meaning all weekdays are included.
        start_date (datetime.datetime, optional): 
            Start of date range to consider. Defaults to `None`, using the dataset's start date. 
        end_date (datetime.datetime, optional):
            End of date range to consider. Defaults to `None`, using the dataset's end date.
        include_double_bookings (bool, optional): 
            If False, exclude double bookings from analysis. Defaults to False.
        include_fixed (bool, optional):
            If False, exclude fixed (non-bookable) desks from analysis. Defaults to True.
        return_user_names (bool, optional): 
            If True, map user IDs to usernames in the output. Defaults to True.
        include_non_booking_users (bool, optional): 
            If True, include users with 0 bookings in the result. Defaults to False.

    Returns:
        FunctionRegistryExpectedFormat: 
            Contains the data and plot of average employee bookings.
    """
    # set default values if applicable
    if return_total_mean is None:
        return_total_mean = False
    if not granularity or not granularity in Dataset._date_format_mapping:
        granularity = 'year'
    if not weekdays:
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    elif isinstance(weekdays, str):
        weekdays = [weekdays.lower()]
    if include_double_bookings is None:
        include_double_bookings = False
    if include_fixed is None:
        include_fixed = True
    if return_user_names is None:
        return_user_names = True
    if include_non_booking_users is None:
        include_non_booking_users = False

    if not include_fixed:
        data = data.drop_fixed()
    if not include_double_bookings:
        data = data.drop_double_bookings()
    if data.empty:
        return FunctionRegistryExpectedFormat()

    if user_ids or user_names:
        user_ids = [] if not user_ids else user_ids
        user_names = [] if not user_names else user_names
        data = data.get_users(user_names, user_ids)

    data = data.get_timeframe(start_date=start_date, end_date=end_date, show_available=False)
    data = data.get_days(weekdays=weekdays)

    column_name = f"avg_bookings_{granularity}"
    data = data.expand_time_intervals_counts(granularity, column_name=column_name)
    def mean(series):
        """Calc the mean for the bookings correctly (with filling possible gaps)"""
        def fill_granularity_gaps(counter: Counter) -> Counter:
            """If there are gaps between the granularity frequency we fill them with zeros (from first to last booking)"""
            periods = counter.keys()
            freq = Dataset._date_format_mapping[granularity]
            return Counter({k: counter.get(k, 0) for k in pd.period_range(start=min(periods), end=max(periods), freq=freq)})
        
        user_sum = fill_granularity_gaps(series.sum())
        mean = sum(user_sum.values()) / len(user_sum)

        return round(mean, 2)
    avg_bookings = data.group_bookings(by="userId", aggregation={column_name: (column_name, mean)}, agg_col_name=column_name)
    if include_non_booking_users:
        missing_user = set(Dataset._userid_username_mapping.keys()) - set(avg_bookings.index)
        missing_user = pd.DataFrame.from_dict(
            {user_id: 0 for user_id in missing_user}, 
            orient="index", 
            columns=avg_bookings.columns
        )
        avg_bookings = pd.concat([avg_bookings, missing_user])
    if num_employees:
        avg_bookings = avg_bookings.sort_bookings(by=column_name, ascending=False).head(num_employees)
        if return_user_names:
            avg_bookings.index = avg_bookings.index.map(Dataset._userid_username_mapping.get)
    
    if return_total_mean:
        avg_bookings = avg_bookings.mean_bookings()
    
    avg_bookings = avg_bookings.to_dict()
    plot = PlotForFunction(
        default_plot=generate_barchart(
            data=avg_bookings,
            title=f"Average bookings per {granularity}",
            xaxis_title="user_name" if return_user_names else "user_id",
            yaxis_title=column_name
        ),
        available_plots=[generate_barchart]
    )

    return FunctionRegistryExpectedFormat(data=avg_bookings, plot=plot)

def get_booking_repeat_pattern(
    data: Dataset,
    user_names: Optional[str | Sequence[str]] = None,
    user_ids: Optional[int | Sequence[int]] = None,
    most_used_desk: Optional[int] = 1,
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"], 
    start_date: Optional[datetime.datetime] = None, 
    end_date: Optional[datetime.datetime] = None,
    include_fixed: Optional[bool] = True,
) -> FunctionRegistryExpectedFormat:
    """
    Identifies users who book the same desks or same days repeatedly.
    
    Args:
        data (Dataset):
            Dataset with booking information.
        user_names (list[str], optional):
            Filter by specific user names. Defaults to `None`, meaning no filtering is applied.
        user_ids (list[int], optional):
            Filter by specific user IDs. Defaults to `None`, meaning no filtering is applied.
        most_used_desk (int, optional):
            Number of top booked desks to consider per user. Defaults to 1, meaning only the most booked desk is considered.
        weekdays (List[str]): 
            List of weekdays to include. If `None`, all weekdays are included.
        start_date (datetime.datetime, optional):
            Start of the analysis period. Defaults to `None`, meaning the dataset's start date is used.
        end_date (datetime.datetime, optional):
            End of the analysis period. Defaults to `None`, meaning the dataset's end date is used.
        include_fixed (bool, optional):
            Whether to include fixed desk bookings. Defaults to True.

    Returns:
        FunctionRegistryExpectedFormat: Contains the data and plots of booking repeat patterns.
    """
    # set default values if applicable
    if not most_used_desk or not isinstance(most_used_desk, int) or most_used_desk < 1:
        most_used_desk = 1
    if not weekdays:
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    elif isinstance(weekdays, str):
        weekdays = [weekdays.lower()]
    if include_fixed is None:
        include_fixed = True

    if not include_fixed:
        data = data.drop_fixed()

    if user_ids or user_names:
        user_ids = [] if not user_ids else user_ids
        user_names = [] if not user_names else user_names
        data = data.get_users(user_names, user_ids)

    if data.empty:
        return FunctionRegistryExpectedFormat()

    # Treating double bookings makes no sense, as no meaningful conclusion can be drawn from them
    data = data.drop_double_bookings()
    data = data.get_timeframe(start_date=start_date, end_date=end_date, show_available=False)
    data = data.get_days(weekdays=weekdays)

    df = data.expand_time_interval_desk_counter(weekdays=weekdays)
    result = (df.sort_values(['userId', 'num_desk_bookings'], ascending=False)
            .groupby('userId')
            .head(most_used_desk)
            .reset_index()
        )

    def df_to_function_data(df, weekdays):
        result = {}
        for day in weekdays:
            result[day.capitalize()] = dict(zip(df['userName'], df[day]))
        return result

    plot_data = df_to_function_data(result, weekdays)
    plot = PlotForFunction(
        default_plot=generate_barchart(
            data=plot_data,
            title="Booking Repeat Pattern",
            xaxis_title="User",
            yaxis_title="Booking Percentage"
        ),
        available_plots=[generate_barchart]
    )
    return FunctionRegistryExpectedFormat(data=plot_data, plot=plot)

def get_booking_clusters(
    data: Dataset,
    co_booking_count_min: Optional[int] = 3, 
    user_ids: Optional[List[int]] = None,
    include_fixed: Optional[bool] = False,
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"], 
    start_date: Optional[datetime.datetime] = None, 
    end_date: Optional[datetime.datetime] = None,
) -> FunctionRegistryExpectedFormat:
    """
    Finds groups of users who frequently book desks close to each other.
    Filters data by users, dates, and weekdays, then identifies clusters based 
    on a minimum number of shared bookings.

    Args:
        data (Dataset):
            Dataset with booking information.
        co_booking_count_min (int, optional):
            Minimum number of shared bookings. Defaults to 3.
        user_ids (List[int], optional):
            List of user IDs to filter by. If `None`, all users are considered.
        include_fixed (bool, optional):
            Whether to include fixed desk bookings. Defaults to False.
        weekdays (List[str]): 
            List of weekdays to include. If `None`, all weekdays are included.
        start_date (datetime.datetime, optional):
            Start of the analysis period. Defaults to `None`, meaning the dataset's start date is used.
        end_date (datetime.datetime, optional):
            End of the analysis period. Defaults to `None`, meaning the dataset's end date is used.

    Returns:
        FunctionRegistryExpectedFormat: 
            Information about the found booking clusters.
    """
    # set default values if applicable
    if not co_booking_count_min or not isinstance(co_booking_count_min, int) or co_booking_count_min < 1:
        co_booking_count_min = 3
    if include_fixed is None:
        include_fixed = False
    if not weekdays:
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    elif isinstance(weekdays, str):
        weekdays = [weekdays.lower()]

    if not include_fixed:
        data = data.drop_fixed()
    # Treating double bookings makes no sense
    data = data.drop_double_bookings()
    data = data.get_timeframe(start_date=start_date, end_date=end_date, show_available=False)
    data = data.get_days(weekdays=weekdays)
    data.expand_time_interval_desk_counter(weekdays=weekdays)
    
    data = data.explode('expanded_desks_day')[['userId', 'userName', 'roomId', 'deskNumber', 'expanded_desks_day']]
    df_paris = booking_graph(data).sort_values("weight", ascending=False)

    mask = df_paris["weight"] >= co_booking_count_min
    df_paris = df_paris[mask]

    result = get_user_workmates(df_paris, user_ids)

    empty_plot = PlotForFunction()
    empty_plot.available_plots = []
    return FunctionRegistryExpectedFormat(data=result, plot=empty_plot)

def get_co_booking_frequencies(
    data: Dataset,
    min_shared_days: Optional[int] = 5, 
    same_room_only: Optional[bool] = None, 
    include_fixed: Optional[bool] = True,
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"], 
    start_date: Optional[datetime.datetime] = None, 
    end_date: Optional[datetime.datetime] = None,
)-> FunctionRegistryExpectedFormat:
    """
    Identifies pairs of users who frequently book on the same days and calculates co-booking statistics.

    This function analyzes booking behavior over a specified timeframe and set of weekdays,
    identifying user pairs who have booked on the same day at least `min_shared_days` times.
    Optionally, it can restrict analysis to bookings in the same room.

    Args:
        data (Dataset):
            Dataset with booking information.
        min_shared_days (int, optional): 
            Minimum number of shared booking days required to include a user pair. Defaults to 5.
        same_room_only (bool, optional):
            Whether to consider only co-bookings where both users were in the same room. Defaults to True. 
        include_fixed (bool, optional):
            Whether to include fixed desk bookings. Defaults to True.
        weekdays (List[str]): 
            List of weekdays to include. If `None`, all weekdays are included.
        start_date (datetime.datetime, optional):
            Start of the analysis period. Defaults to `None`, meaning the dataset's start date is used.
        end_date (datetime.datetime, optional):
            End of the analysis period. Defaults to `None`, meaning the dataset's end date is used.

    Returns:
        FunctionRegistryExpectedFormat:
    """
    # set default values if applicable
    if not min_shared_days or not isinstance(min_shared_days, int) or min_shared_days < 1:
        min_shared_days = 5
    if same_room_only is None:
        same_room_only = True
    if include_fixed is None:
        include_fixed = True
    if not weekdays:
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    elif isinstance(weekdays, str):
        weekdays = [weekdays.lower()]

    if not include_fixed:
        data = data.drop_fixed()
    if not weekdays:
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    # Treating double bookings makes no sense
    data = data.drop_double_bookings()
    data = data.get_timeframe(start_date=start_date, end_date=end_date, show_available=False)
    data = data.get_days(weekdays=weekdays)
    data.expand_time_interval_desk_counter()

    data = data.explode('expanded_desks_day')[['userId', 'userName', 'roomId', 'expanded_desks_day']]
    booking_counter = data["userId"].value_counts().reset_index()
    booking_counter = booking_counter.rename(columns={"count": "total_bookings"})

    pairs_df = count_co_bookings(data, include_room=same_room_only)
    if min_shared_days:
        pairs_df = pairs_df[pairs_df["count"] >= min_shared_days]

    merged = merge_dataframes(
        df_1=pairs_df,
        df_2=booking_counter,
        left_column="userId_1",
        right_column="userId",
        how="left",
        rename={"total_bookings": "total_bookings_user1"},
        drop_columns=["userId"]
    )
    merged = calc_percent(
        merged, 
        "count", 
        "total_bookings_user1", 
        "share_1"
    )

 
    merged = merge_dataframes(
        df_1=merged,
        df_2=booking_counter,
        left_column="userId_2",
        right_column="userId",
        how="left",
        rename={"total_bookings": "total_bookings_user2"},
        drop_columns=["userId"]
    )
    merged = calc_percent(
        merged, 
        "count", 
        "total_bookings_user2",
        "share_2"
    )



    # Barchart (Data)
    plot_dict_barchart = (
        merged.sort_values(["userId_1", "share_1"], ascending=False)
        .groupby("userId_1")
        .apply(lambda df: dict(zip(df["userId_2"], df["share_1"])))
        .to_dict()
    )
    plot = PlotForFunction(
        default_plot=generate_barchart(
            plot_dict_barchart,
            title="Co-Booking Share per User",
            xaxis_title="UserId2",
            yaxis_title="Share (%)"
        ),
        available_plots=[generate_barchart]
    )
    return FunctionRegistryExpectedFormat(data=plot_dict_barchart, plot=plot)



# --------- Helpers --------- #

def merge_dataframes(
    df_1: pd.DataFrame,
    df_2: pd.DataFrame,
    left_column: str = "userId_1",
    right_column: str = "userId",
    how: str = "left",
    drop_columns: Optional[List[str]] = None,
    rename: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    merged = pd.merge(df_1, df_2, left_on=left_column, right_on=right_column, how=how)

    if rename:
        merged = merged.rename(columns=rename)

    if drop_columns:
        cols_to_drop = [col for col in drop_columns if col in merged.columns]
        merged = merged.drop(columns=cols_to_drop)

    return merged

def calc_percent(
    df: pd.DataFrame,
    numerator_col: str,
    denominator_col: str,
    result_col: str,
    round_digits: int = 2
) -> pd.DataFrame:
    df[result_col] = (df[numerator_col] / df[denominator_col] * 100).round(round_digits)
    return df

def count_co_bookings(dataset: pd.DataFrame, include_room: bool = False) -> pd.DataFrame:
    pair_counts = Counter()
    if not include_room:
        dataset = dataset.copy()
        dataset['roomId'] = "__any__"

    for (_, group) in dataset.groupby(['expanded_desks_day', 'roomId']):
        users = sorted(set(group['userId']))
        for u1, u2 in combinations(users, 2):
            pair_counts[(u1, u2, group['roomId'].iloc[0])] += 1

    pairs_df = pd.DataFrame([
        {'userId_1': u1, 'userId_2': u2, 'roomId': room, 'count': count}
        for (u1, u2, room), count in pair_counts.items()
    ])

    if not include_room:
        pairs_df = pairs_df.drop(columns='roomId')

    return pairs_df

def booking_graph(df: pd.DataFrame):
    grouped = df.groupby(['expanded_desks_day', 'roomId'])['userId'].apply(list)
    pair_counts = Counter()

    for (date, room), users in grouped.items():
        unique_users = sorted(set(users))
        for u1, u2 in combinations(unique_users, 2):
            pair_counts[(u1, u2)] += 1

    df_pairs = pd.DataFrame([
            {'userId_1': u1, 'userId_2': u2, 'weight': weight}
            for (u1, u2), weight in pair_counts.items()
        ])

    return df_pairs

def get_user_workmates(
    df: pd.DataFrame,
    user_ids: Optional[list[int]],
    col_name_user1: str = "userId_1",
    col_name_user2: str = "userId_2"
) -> dict[int, list[int]]:
    if user_ids is None:
        return df.to_dict()
    workmate_dict = {}

    for user_id in user_ids:
        partners_1 = df.loc[df[col_name_user1] == user_id, col_name_user2].tolist()
        partners_2 = df.loc[df[col_name_user2] == user_id, col_name_user1].tolist()
        all_partners = list(set(partners_1 + partners_2))
        workmate_dict[user_id] = all_partners

    return workmate_dict

# --------- Testing --------- #
if __name__ == "__main__":
    from deskquery.data.dataset import create_dataset
    dataset = create_dataset()  
    # double_bookings = dataset.get_double_bookings()
    # print(double_bookings)

    start_date_str = "2022.12.19"
    end_date_str = "2025.05.30"
    start_date_obj = datetime.datetime.strptime(start_date_str, "%Y.%m.%d")
    end_date_obj = datetime.datetime.strptime(end_date_str, "%Y.%m.%d")

