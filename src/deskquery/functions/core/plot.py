#!/usr/bin/env python 
from typing import Optional, Dict
from deskquery.functions.types import FunctionRegistryExpectedFormat, Plot, PlotFunction, PlotForFunction
from deskquery.functions.core.helper.plot_helper import (
    generate_heatmap,
)

def generate_plot_for_function(
    function_result: FunctionRegistryExpectedFormat,
    additional_plot_args: Dict[str, str] = {},
    plot_to_generate: Optional[PlotFunction] = None,
    use_default_plot: bool = True
) -> dict:
    """
    Takes a function result and creates a visualization of the data.
    Therefore, a specific plot function or the function results default plot may be used.

    Args:
        function_result (FunctionRegistryExpectedFormat):
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
        FunctionRegistryExpectedFormat:
            A FunctionRegistryExpectedFormat object containing the given data and the specified plot.

    Raises:
        ValueError: If no plot is available and `use_default_plot` is `False`.
        ValueError: If the specified `plot_to_generate` is not available for the function result.
    """
    data = function_result.data
    plot = function_result.plot

    if not plot.available_plots and not use_default_plot:
        raise ValueError(
            "Unfortunately, there are no other plots than the default one available for this function result."
        )
    if not plot.available_plots:
        raise ValueError(
            "Unfortunately, there are no plots available for this function result."
        )
    # if there is no plot to generate defined but the default plot is available
    if not plot_to_generate and use_default_plot and plot.default_plot:
        # enable plotting in the frontend
        function_result.plotted = True
        return function_result
    # if there is no plot to generate defined and the default plot should not be used
    # but there is another plot than the default one available
    elif (not plot_to_generate and len(plot.available_plots) > 1 and (
          use_default_plot and not plot.default_plot or not use_default_plot)):
        plot_to_generate = plot.available_plots[1]
    
    # plot.available_plots should not be empty here
    if plot_to_generate == plot.available_plots[0]:
        use_default_plot = True
    else:
        use_default_plot = False

    if use_default_plot:
        # enable plotting in the frontend
        function_result.plotted = True
        return function_result
    else:
        # plot_to_generate has to be a function from the plot function filled with arguments
        if plot_to_generate in plot.available_plots:
            return FunctionRegistryExpectedFormat(
                data=data,
                plot=PlotForFunction(
                    default_plot=plot_to_generate(
                        data, **additional_plot_args
                    ),
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
