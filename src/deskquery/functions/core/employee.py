#!/usr/bin/env python 
from typing import Optional, List, Literal, Sequence, Dict
from datetime import datetime
import pandas as pd
from collections import Counter
from itertools import combinations
from deskquery.data.dataset import Dataset
from deskquery.functions.types import FunctionRegistryExpectedFormat, PlotForFunction
from deskquery.functions.core.helper.plot_helper import generate_heatmap, generate_barchart, generate_hist, generate_map

def get_avg_employee_bookings(
    data: Dataset,
    user_names: Optional[str | Sequence[str]] = None,
    user_ids: Optional[int | Sequence[int]] = None,
    num_employees: Optional[int] = None,
    return_total_mean: bool = False,
    granularity: Literal["day", "week", "month", "year"] = 'year',
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    include_double_bookings: bool = False,
    include_fixed: bool = True,
    return_user_names: bool = True,
    include_non_booking_users: bool = False
) -> FunctionRegistryExpectedFormat:
    """
    Compute average booking frequency per employee over a specified time granularity.

    Parameters:
        data (Dataset): Dataset containing booking records.
        user_names (str | Sequence[str], optional): Filter for specific usernames.
        user_ids (int | Sequence[int], optional): Filter for specific user IDs.
        num_employees (int, optional): Limit result to top-N employees by average bookings.
        return_total_mean (bool): If True, return the mean over all employees instead of per-user values.
        granularity (str): Time unit for averaging. One of "day", "week", "month", or "year".
        weekdays (List[str]): Days of the week to include in the analysis.
        start_date (datetime, optional): Start of date range to consider.
        end_date (datetime, optional): End of date range to consider.
        include_double_bookings (bool): If False, exclude double bookings from analysis.
        include_fixed (bool): If False, exclude fixed (non-bookable) desks from analysis.
        return_user_names (bool): If True, map user IDs to usernames in the output.
        include_non_booking_users (bool): If True, include users with 0 bookings in the result.

    Returns:
        FunctionRegistryExpectedFormat: Contains the data and plots of booking average bookings.
    """
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
        missing_user = pd.DataFrame.from_dict({user_id: 0 for user_id in missing_user}, 
                                              orient="index", 
                                              columns=avg_bookings.columns)
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
            title=column_name,
            xaxis_title="user_name" if return_user_names else "user_id",
            yaxis_title=column_name
        ),
        available_plots=[generate_barchart, generate_heatmap]
    )

    return FunctionRegistryExpectedFormat(data=avg_bookings, plot=plot)

def get_booking_repeat_pattern(
    data: Dataset,
    user_names: Optional[str | Sequence[str]] = None,
    user_ids: Optional[int | Sequence[int]] = None,
    most_used_desk: int = 1,
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None,
    include_fixed: bool = True,
) -> FunctionRegistryExpectedFormat:
    """
    Identifies users who book the same desks or same days repeatedly.
    
    Args:
        data (Dataset): The booking dataset to analyze.
        user_names (Optional[list[str]]): Filter by specific user names.
        user_ids (Optional[list[int]]): Filter by specific user IDs.
        most_used_desk (int): Number of top booked desks to consider per user.
        weekdays (List[str]): List of weekdays to include.
        start_date (Optional[datetime]): Start of the analysis period.
        end_date (Optional[datetime]): End of the analysis period.
        include_fixed (bool): Whether to include fixed desk bookings.

    Returns:
        FunctionRegistryExpectedFormat: Contains the data and plots of booking repeat patterns.
    """
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
        available_plots=[generate_barchart, generate_heatmap]
    )
    return FunctionRegistryExpectedFormat(data=plot_data, plot=plot)

def get_booking_clusters(
    data: Dataset,
    co_booking_count_min: int = 3, 
    user_ids: Optional[list[int]] = None,
    include_fixed: bool = False,
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None,
) -> FunctionRegistryExpectedFormat:
    """
    Finds groups of users who frequently book desks close to each other.
    Filters data by users, dates, and weekdays, then identifies clusters based 
    on a minimum number of shared bookings.

    Args:
        data (Dataset): Booking data.
        co_booking_count_min (int): Minimum number of shared bookings.
        user_ids (Optional[list[int]]): list of user IDs to filter by.
        include_fixed (bool): excludes fixed desk bookings from analysis.
        weekdays (List[str]): weekdays to consider.
        start_date (Optional[datetime]): start date.
        end_date (Optional[datetime]): end date.

    Returns:
        FunctionRegistryExpectedFormat: 
            Information about the found booking clusters.
    """
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

    # Heatmap (Data)
    # z = result["weight"]
    # x = result["userId_1"]
    # y = result["userId_2"]
    # title="Co-Booking Heatmap",
    # xaxis_title="User ID 2",
    # yaxis_title="User ID 1",

    # Todo: None is not currently being treated
    return FunctionRegistryExpectedFormat(data=result, plot=PlotForFunction())

def get_co_booking_frequencies(
    data: Dataset,
    min_shared_days: int = 5, 
    same_room_only: Optional[bool] = None, 
    include_fixed: bool = True,
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None,
)-> FunctionRegistryExpectedFormat:
    """
    Identifies pairs of users who frequently book on the same days and calculates co-booking statistics.

    This function analyzes booking behavior over a specified timeframe and set of weekdays,
    identifying user pairs who have booked on the same day at least `min_shared_days` times.
    Optionally, it can restrict analysis to bookings in the same room.

    Args:
        data (Dataset): Dataset with booking information.
        min_shared_days (int): minimum number of shared booking days required to include a user pair.
        same_room_only (bool): only consider co-bookings where both users were in the same room.
        include_fixed (bool): excludes fixed desk bookings from analysis.
        weekdays (List[str]): weekdays to consider for the analysis (e.g., ["monday", "wednesday"]).
        start_date (Optional[datetime]): start date 
        end_date (Optional[datetime]): end date

    Returns:
        FunctionRegistryExpectedFormat:
    """
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

    # Heatmap (Data)
    # heatmap_df = merged.pivot(index="userId_1", columns="userId_2", values="count").fillna(0)
    # z = heatmap_df.values,
    # x = heatmap_df.columns.astype(str),
    # y = heatmap_df.index.astype(str)
    # title = "Co-Booking Counts Heatmap"
    # xaxis_title="UserId 2",
    # yaxis_title="UserId 1"


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
        available_plots=[generate_barchart, generate_heatmap]
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
    start_date_obj = datetime.strptime(start_date_str, "%Y.%m.%d")
    end_date_obj = datetime.strptime(end_date_str, "%Y.%m.%d")

