#!/usr/bin/env python 
from typing import Optional, List, Callable
from datetime import datetime
import plotly.graph_objects as go
from deskquery.functions.types import FunctionRegistryExpectedFormat, PlotForFunction, Plot, PlotFunction
from deskquery.functions.core.helper.plot_helper import generate_heatmap, generate_hist, generate_barchart, generate_scatterplot, generate_lineplot, generate_map, generate_table

# TODO: Think of a way to add them smart to generate_plot_for_function since thats
# TODO: the only summary the llm sees to pick the correct plot
helper_docstrings = {
    "generate_heatmap": generate_heatmap.__doc__,
    "generate_hist": generate_hist.__doc__,
    "generate_barchart": generate_barchart.__doc__,
    "generate_scatterplot": generate_scatterplot.__doc__,
    "generate_lineplot": generate_lineplot.__doc__,
    "generate_map": generate_map.__doc__,
    "generate_table": generate_table.__doc__
}

def generate_plot_for_function(
    func_result: FunctionRegistryExpectedFormat,
    additional_plot_args: dict[str, str] = {},
    plot_to_generate: Optional[PlotFunction] = None,
    use_default_plot: bool = True
) -> dict:

    data = func_result.data
    plot = func_result.plot

    if not plot.available_plots:
        return {
            "status": "not_available",
            "message": "Unfortunately there are no other plots available for this function result."
        }

    if plot_to_generate:
        use_default_plot = False

    if use_default_plot:
        return {
            "status": "success",
            "plot": plot.default_plot.to_json(),
        }
    else:
        # plot_to_generate has to be a function from the plot function filled with arguments from llm
        if plot_to_generate in plot.available_plots:
            return {
                "status": "success",
                "plot": plot_to_generate(data, **additional_plot_args)
            }
        else:
            return {
                "status": "not_available"
                "Unfortunately the desired plot is not available for this function result."
            }

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
