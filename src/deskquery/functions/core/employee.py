#!/usr/bin/env python 
from typing import Optional, List, Literal
from datetime import datetime
import json

from plotly.utils import PlotlyJSONEncoder
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import plotly.graph_objs as go
import plotly.express as px
from collections import Counter

from deskquery.data.dataset import Dataset
from deskquery.functions.types import FunctionRegistryExpectedFormat

def get_avg_employee_bookings(
    dataset: Dataset,
    num_employees: int = 10,
    return_total_mean: bool = False,
    granularity: Literal["day", "week", "month", "year"] = 'year',
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    include_double_bookings: bool = False,
    include_fixed: bool = True,
) -> FunctionRegistryExpectedFormat:
    """
    Calculates average bookings per employee per day, week, month or year.
    """
    if not include_fixed:
        dataset = dataset.drop_fixed()
    if not include_double_bookings:
        dataset = dataset.drop_double_bookings()

    dataset = dataset.get_timeframe(start_date=start_date, end_date=end_date, show_available=False)
    dataset = dataset.get_days(weekdays=weekdays)

    column_name = f"avg_bookings_{granularity}"
    dataset = dataset.expand_time_intervals_counts(granularity, column_name=column_name)

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
    avg_bookings = dataset.group_bookings(by="userId", aggregation={column_name: (column_name, mean)}, agg_col_name=column_name)
    if num_employees:
        avg_bookings = avg_bookings.sort_values(by=column_name, ascending=False).head(num_employees)
    if return_total_mean:
        avg_bookings = avg_bookings.mean()

    return {
        "data": avg_bookings.to_dict(),
        "plotable": True
    }

def get_booking_repeat_pattern(
    dataset: Dataset,
    most_used_desk: int = 1, # TO DO: Still needs to be implemented 
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None,
    include_fixed: bool = True,
) -> FunctionRegistryExpectedFormat:
    """
    Identifies users who book the same desks or same days repeatedly.

    Args:
        most_used_desk: If several tables are booked, specifies how many tables should be issued
        weekdays: Days of interest.
        start_date: Start date.
        end_date: End date.

    Returns:
    """
    if not include_fixed:
        dataset = dataset.drop_fixed()
    # Treating double bookings makes no sense, as no meaningful conclusion can be drawn from them
    dataset = dataset.drop_double_bookings()
    dataset = dataset.get_timeframe(start_date=start_date, end_date=end_date, show_available=False)
    dataset = dataset.get_days(weekdays=weekdays)
    df = dataset.expand_time_interval_desk_counter(weekdays=weekdays)

    df.loc[:, weekdays] = (df.loc[:, weekdays].div(df["num_desk_bookings"], axis=0)* 100).round(2)
    df["percentage_of_user"] = (df['num_desk_bookings'] / df.groupby(level='userId')['num_desk_bookings'].transform('sum') * 100).round(2)
    result = df.loc[df.groupby('userId')['num_desk_bookings'].idxmax()]
    result = result.iloc[:, :-2].reset_index()

    return {
        "data": result.to_dict(),
        "plotable": True
    }

def get_booking_clusters(
    dataset: Dataset,
    distance_threshold: float = 3, 
    co_booking_count_min: int = 3, 
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"], 
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
    dataset = dataset.get_timeframe(start_date=start_date, end_date=end_date, show_available=False)
    dataset = dataset.get_days(weekdays=weekdays)

    cluster_results = []

    for (blockedFrom, roomID), group in dataset.to_df().groupby(['blockedFrom', 'roomId']):
        coords = group["deskNumber"].values.reshape(-1, 1)
        if len(coords) >= co_booking_count_min:
            clustering = DBSCAN(eps=distance_threshold, min_samples=co_booking_count_min).fit(coords)
            group = group.copy()
            group['cluster'] = clustering.labels_  # Cluster-Label -1 = no Cluster
            cluster_results.append(group)

    if not cluster_results:
        return pd.DataFrame()
    
    result_df = pd.concat(cluster_results).reset_index(drop=True)

    result_df = result_df[result_df['cluster'] != -1]

    grouped = result_df.groupby(['blockedFrom', 'roomId', 'cluster'])['userName'].apply(list).reset_index()

    html = grouped.to_html(index=False, classes="table table-striped")
    return {""}

def get_co_booking_frequencies(
    dataset: Dataset,
    min_shared_days: int = None, 
    same_room_only: bool = None, 
    include_fixed: bool = True,
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"], 
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
    # gibt es Mitarbeiter, die immer am gleichen Tag arbeiten?
    # gibt es Mitarbeiter die sich öfters im Büro sehen?
    
    # min shared -> wie oft die Leute zusammen buchen mit einem treshhold
    # 

    if not include_fixed:
        dataset = dataset.drop_fixed()
    # Treating double bookings makes no sense
    dataset = dataset.drop_double_bookings()

    dataset = dataset.get_timeframe(start_date=start_date, end_date=end_date, show_available=False)
    dataset = dataset.get_days(weekdays=weekdays)
    desks = dataset.expand_time_intervals_desks("day")
    
    dataset = dataset.sort_values("blockedFrom")
    print(dataset)
    




if __name__ == "__main__":
    from deskquery.data.dataset import create_dataset
    dataset = create_dataset()  
    # double_bookings = dataset.get_double_bookings()
    # print(double_bookings)

    result = get_booking_repeat_pattern(dataset, include_fixed=False)
    df = pd.DataFrame(result["data"])
    print(df)

    