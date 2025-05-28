#!/usr/bin/env python 
from typing import Optional, List, Callable
from datetime import datetime
import plotly.graph_objects as go
from deskquery.functions.types import FunctionRegistryExpectedFormat, PlotForFunction, Plot, PlotFunction
from typing import Sequence 

def generate_plot_for_function(plot: PlotForFunction,
                               additional_plot_args: dict[str, str] = {},
                               plot_to_generate: Optional[PlotFunction] = None, 
                               use_default_plot: bool = True) -> Plot | str:
    if not plot.available_plots:
        # TODO: Maybe rather return a PlotForFunction Object with an overload to provide the string to handle it better later?
        return "Not plot available for this kind of data."

    # Not needed since we will always call a function before and if default plot is not set there are anyway no available plots
    # if not plot.default_plot and not additional_plot_args:

    if use_default_plot:
        return plot.default_plot
    else:
        # plot_to_generate has to be a function from the plot function filled with arguments from llm
        if plot_to_generate in plot.available_plots:
            return plot_to_generate(**additional_plot_args)
        else:
            return "The asked plot is not available for this kind of data."

if __name__ == "__main__":
    from deskquery.functions.core.employee import get_avg_employee_bookings
    from deskquery.data.dataset import create_dataset
    dataset = create_dataset()
    response = get_avg_employee_bookings(dataset)
    plot_response = generate_plot_for_function(response["plot"])
    if isinstance(plot_response, Plot):
        plot_response.write_html("hist.html")
    else:
        print(plot_response)
