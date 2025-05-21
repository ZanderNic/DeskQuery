#!/usr/bin/env python 
from typing import Optional, List
from datetime import datetime
import json
from flask import current_app

from plotly.utils import PlotlyJSONEncoder
import pandas as pd
from sklearn.cluster import DBSCAN
import plotly.graph_objs as go
import plotly.express as px

from deskquery.data.dataset import Dataset


def get_avg_booking_per_employee(
    dataset: Dataset,
    num_employees: int = 10,
    granularity: str = 'week',
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    """
    Calculates average bookings per employee by week or month.
    """
    col_name = f"avg_user_bookings_{granularity}"
    dataset = dataset.get_timeframe(start_date=start_date, end_date=end_date, show_available=False)
    dataset = dataset.get_days(weekdays=weekdays)
    dataset = dataset.add_time_interval_counts(granularity)
    dataset = dataset.group_bookings(by="userId", aggregation=("interval_count", 'sum'), agg_col_name=col_name)
    if num_employees:
        dataset = dataset.sort_values(by=col_name, ascending=False).head(num_employees)

    return {
        "data": dataset.to_dict(),
        "plotable": True
    }

def get_booking_repeat_pattern(
    dataset: Dataset,
    min_repeat_count: int = 2, 
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> None:
    """
    Identifies users who book the same desks repeatedly.

    Args:
        min_repeat_count: Minimum number of repeated bookings.
        weekdays: Days of interest.
        start_date: Start date.
        end_date: End date.

    Returns:
    """
    dataset = dataset.get_timeframe(start_date=start_date, end_date=end_date, show_available=False)
    dataset = dataset.get_days(weekdays=weekdays)

    group = dataset.groupby(['userId','userName', 'deskId']).size().reset_index(name='count')
    result = group[group['count'] >= min_repeat_count ].sort_values(by='count', ascending=False)
    
    result = result.head(10)

    html = result[['userName', 'deskId', 'count']].to_html(index=False, classes="table table-striped")
    
    return {
        "type": "html_table",
        "text": "",
        "html": html
    }

def get_booking_repeat_pattern_plot(
    dataset: Dataset,
    min_repeat_count: int = 2, 
    weekdays: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> dict:
    """
    Identifies users who book the same desks repeatedly and returns a plot.

    Args:
        min_repeat_count: Minimum number of repeated bookings.
        weekdays: Days of interest.
        start_date: Start date.
        end_date: End date.

    Returns:
        dict: Containing the plotly plot as HTML.
    """
    dataset = dataset.get_timeframe(start_date=start_date, end_date=end_date, show_available=False)
    dataset = dataset.get_days(weekdays=weekdays)

    # Group by userId, userName, and deskId, and count the occurrences
    group = dataset.groupby(['userId', 'userName', 'deskId']).size().reset_index(name='count')
    result = group[group['count'] >= min_repeat_count].sort_values(by='count', ascending=False)
    
    # Limit the result to top 10
    result = result.head(10)

    # Plot data using Plotly
    trace = go.Bar(
        x=result['userName'],
        y=result['count'],
        text=result['userName'],  # Show names on hover
        hoverinfo='text+y',  # Show user names and counts
        marker=dict(color='rgb(26, 118, 255)')  # Custom color for bars
    )

    layout = go.Layout(
        title='Top 10 Users with the Most Repeated Desk Bookings',
        xaxis=dict(title='User Name'),
        yaxis=dict(title='Repeat Count'),
        template='plotly_dark'
    )

    fig = go.Figure(data=[trace], layout=layout)

    plot_data = json.loads(json.dumps(fig.data, cls=PlotlyJSONEncoder))
    plot_layout = json.loads(json.dumps(fig.layout, cls=PlotlyJSONEncoder))
    return {
        "type": "plot",
        "html": "",
        "data": plot_data,
        "layout": plot_layout,
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
    min_shared_days: int, 
    same_room_only: bool, 
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
    pass

if __name__ == "__main__":
    from deskquery.data.dataset import create_dataset
    get_avg_booking_per_employee(create_dataset())