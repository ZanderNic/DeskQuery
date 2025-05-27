#!/usr/bin/env python 
from typing import Optional, List, Callable
from datetime import datetime
import plotly.graph_objects as go
from deskquery.functions.types import FunctionRegistryExpectedFormat, PlotForFunction, PlotFunctionReturnFormat  

# def generate_plot_for_function(use_default_plot: bool = True, plot_to_generate):
#     # get the data from the history from the response before and feed it into the plot function
#     # func = function_registry[response["function"]]
#     # data = func(**response["parameters"])
#     if PlotForFunction:
#         if use_default_plot:
#             return PlotForFunction.default_plot
#         else:
#             # plot_to_generate has to be a function from the plot function filled with arguments from llm
#             if plot_to_generate in PlotForFunction.avaiable_plots:
#                 return plot_to_generate
#     else:
#         return "You first have to execute a function before you can use this method."

def create_plotly_figure():
    pass

def generate_heatmap(data: FunctionRegistryExpectedFormat, 
                      title: Optional[str] = None, 
                      xaxis_title: Optional[str] = None,
                      yaxis_title: Optional[str] = None
                      ) -> PlotFunctionReturnFormat:
    """ 
    Generates a heatmap showing desk bookings over time.

    Args:
        by_room: If True, shows heatmap per room.
        resolution: Time resolution of heatmap: 'daily', 'weekly', or 'monthly'.
        weekdays: Days of the week to include.
        start_date: Start date for data.
        end_date: End date for data.

    Returns:

    """
    fig = go.Figure()

    for trace_name, trace_data in data.items():
        fig.add_trace(
            go.Heatmap(
                z=z_data,
                x=x_labels,
                y=y_labels,
                colorscale='Viridis'
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        template="plotly_white",
        bargap=0.15,
        font=dict(size=14),
        margin=dict(l=40, r=40, t=60, b=40)
    )

    return fig

def generate_barchart(data: FunctionRegistryExpectedFormat, 
                      title: Optional[str] = None, 
                      xaxis_title: Optional[str] = None,
                      yaxis_title: Optional[str] = None
                      ) -> PlotFunctionReturnFormat:
    """Generates a barchart"""
    fig = go.Figure()

    for trace_name, trace_data in data.items():
        fig.add_trace(
            go.Bar(
                name=trace_name,
                x=list(trace_data.keys()),
                y=list(trace_data.values()),
                textposition="auto",
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        template="plotly_white",
        bargap=0.15,
        font=dict(size=14),
        margin=dict(l=40, r=40, t=60, b=40)
    )

    return fig

def generate_hist(data: FunctionRegistryExpectedFormat,
                  nbinsx: Optional[int] = None,
                  title: Optional[str] = None, 
                  xaxis_title: Optional[str] = None,
                  yaxis_title: Optional[str] = None
                  ) -> PlotFunctionReturnFormat:
    """Generates a histogramm"""
    fig = go.Figure()

    for trace_name, trace_data in data.items():
        fig.add_trace(go.Histogram(name=trace_name,
                                   x=list(trace_data.values()),
                                   nbinsx=nbinsx if nbinsx else len(trace_data.values())))

    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        template="plotly_white",
        bargap=0.15,
        font=dict(size=14),
        margin=dict(l=40, r=40, t=60, b=40)
    )

    return fig

def generate_map():
    """Generates the given room map"""
    pass

def generate_plot_interactive(
    by_room: bool, 
    resolution: str, weekdays: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> None:
    """
    Produces an interactive plot of desk booking data.

    Args:
        by_room: If True, plots are grouped by room.
        resolution: Level of temporal detail ('daily', 'weekly', etc.).
        weekdays: Days of interest.
        start_date: Analysis start date.
        end_date: Analysis end date.

    Returns:
    
    """
    pass


def generate_plot(
    by_room: bool, 
    resolution: str, 
    desk: int, 
    weekdays: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> None:
    """
    Creates a plot of desk utilization over time.

    Args:
        by_room: If True, groups data by room.
        resolution: Time granularity.
        desk: Desk ID or 'all' to include all desks.
        weekdays: Relevant weekdays.
        start_date: Starting date.
        end_date: Ending date.

    Returns:

    """
    pass

if __name__ == "__main__":
    from deskquery.data.dataset import create_dataset
    from deskquery.functions.core.employee import get_avg_employee_bookings
    dataset = create_dataset()

    result = get_avg_employee_bookings(dataset, num_employees=200, include_fixed=False)
    fig = generate_hist(result)
    fig.write_html("hist.html")