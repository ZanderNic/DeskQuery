#!/usr/bin/env python 
from typing import Optional, Dict
from deskquery.functions.types import FunctionRegistryExpectedFormat, Plot, PlotFunction, PlotForFunction
from deskquery.functions.core.helper.plot_helper import (
    generate_heatmap,
    generate_hist,
    generate_barchart,
    generate_scatterplot,
    generate_lineplot,
    generate_map,
    generate_table
)

# TODO: Think of a smart way to add them to generate_plot_for_function since that's
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
    additional_plot_args: Dict[str, str] = {},
    plot_to_generate: Optional[PlotFunction] = None,
    use_default_plot: bool = True
) -> dict:
    """
    Takes a function result and creates a visualization of the data.
    Therefore, a specific plot function or the function results default plot may be used.

    Args:
        func_result (FunctionRegistryExpectedFormat):
            Function result object containing a FunctionData and PlotForFunction object.
        additional_plot_args (Dict[str, str]):
            A dict with keyword arguments for the plot creation usually containing the keys "title"
            for the main plot title, "xaxis_title" and "yaxis_title" for specific axes titles.
        plot_to_generate (PlotFunction, optional):
            The PlotFunction to use for the visualization indicating the plot type. The choices are given by the
            function result's available plots. If this is `None`, the default plot for the result data is used.
        use_default_plot (bool):
            If `True`, the function result's predefined default plot type is used.
            If `False`, another available plot than the default one must be specified as `plot_to_generate` to not
            result in an error.

    Returns:
        dict:
            A json like message with a "status" field indicating the success of the plot creation
            and either a "message" filed with the error message or a "plot" field with the plot data.
    """
    data = func_result.data
    plot = func_result.plot

    if not plot.available_plots and not use_default_plot:
        raise ValueError(
            "Unfortunately, there are no other plots than the default one available for this function result."
        )

    if plot_to_generate:
        use_default_plot = False

    if use_default_plot:
        # enable plotting in the frontend
        func_result.plotted = True
        return func_result
    else:
        # plot_to_generate has to be a function from the plot function filled with arguments
        if plot_to_generate in plot.available_plots:
            return FunctionRegistryExpectedFormat(
                data=data,
                plot=PlotForFunction(
                    default_plot=plot_to_generate(
                        data, 
                        title=plot.default_plot['layout']['title']['text'], 
                        xaxis_title=plot.default_plot['layout']['xaxis']['title']['text'],
                        yaxis_title=plot.default_plot['layout']['yaxis']['title']['text']),
                    available_plots=plot.available_plots
                ),
                plotted=True
            )
        else:
            raise ValueError(
                f"The plot function {plot_to_generate.__name__} is not available for this function result."
            )

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
