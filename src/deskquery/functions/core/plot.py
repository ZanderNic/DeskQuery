#!/usr/bin/env python 
from typing import Optional, List, Callable
from datetime import datetime
import plotly.graph_objects as go
from deskquery.functions.types import FunctionRegistryExpectedFormat, PlotForFunction, Plot, PlotFunction

def generate_plot_for_function(func_result: FunctionRegistryExpectedFormat,
                               additional_plot_args: dict[str, str] = {},
                               plot_to_generate: Optional[PlotFunction] = None, 
                               use_default_plot: bool = True) -> Plot | str:

    data = func_result.data
    plot = func_result.plot

    if not plot.available_plots:
        return "Not plot available for this kind of data."

    if plot_to_generate:
        use_default_plot = False

    if use_default_plot:
        return plot.default_plot
    else:
        # plot_to_generate has to be a function from the plot function filled with arguments from llm
        if plot_to_generate in plot.available_plots:
            return plot_to_generate(data, **additional_plot_args)
        else:
            return "The asked plot is not available for this kind of data."

if __name__ == "__main__":
    from deskquery.functions.core.employee import get_avg_employee_bookings, generate_heatmap
    from deskquery.data.dataset import create_dataset
    dataset = create_dataset()
    response = get_avg_employee_bookings(dataset, num_employees=20)

    plot_response = generate_plot_for_function(response, plot_to_generate=generate_heatmap)
    if isinstance(plot_response, Plot):
        plot_response.write_html("hist.html")
    else:
        print(plot_response)
