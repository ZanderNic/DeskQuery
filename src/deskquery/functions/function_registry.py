from pathlib import Path
from deskquery.functions.core.plot import *
from deskquery.functions.core.policy import *
from deskquery.functions.core.utilization import * 
from deskquery.functions.core.employee import *
from deskquery.functions.core.forecasting import *
import inspect

function_registry = {
    # Utilization
    "mean_utilization": mean_utilization,
    "utilization_stats": utilization_stats,
    "detect_utilization_anomalies": detect_utilization_anomalies,

    # Policy
    "simulate_policy": simulate_policy,
    "detect_policy_violations": detect_policy_violations,
    "suggest_balanced_utilization_policy": suggest_balanced_utilization_policy,
    "compare_utilization_before_after_policy": compare_utilization_before_after_policy,

    # Employee behavior
    "get_avg_employee_bookings": get_avg_employee_bookings,
    "get_booking_repeat_pattern": get_booking_repeat_pattern,
    "get_booking_clusters": get_booking_clusters,
    "get_co_booking_frequencies": get_co_booking_frequencies,

    # Plotting
    "generate_heatmap": generate_heatmap,
    "generate_plot_interactive": generate_plot_interactive,
    "generate_plot": generate_plot,

    # Capacity & Forecasting
    "estimate_table_needs": estimate_table_needs,
    "forecast_desk_demand": forecast_desk_demand,
    "simulate_room_closure": simulate_room_closure,
    "estimate_max_employees_per_room": estimate_max_employees_per_room,
}
 
def create_function_summaries():
    function_summaries = ""
    to_remove = []

    for name, func in function_registry.items():
        try:
            source_lines = inspect.getsource(func).strip().splitlines()
            # we only want the declaration not the whole function code. so we search for the first line that ends with ":"
            declaration_lines = []
            for line in source_lines:
                declaration_lines.append(line)
                if line.strip().endswith(":"):
                    break

            declaration = "\n".join(declaration_lines)
            docstring = inspect.getdoc(func)

            if declaration and docstring:
                function_summaries += declaration + "\n"
                function_summaries += docstring + "\n"
                function_summaries += "\n-\n\n"
            else:
                # if the function doesn´t exist or the docstring misses its deleted from the function_registry
                to_remove.append(name)

        except (TypeError, OSError):
            continue

    for name in to_remove:
        del function_registry[name]

    return function_summaries

function_summaries = create_function_summaries()

# print(function_summaries)

description_path = Path(__file__).resolve().parent / 'function_summaries_export.txt' 
with open(description_path, 'w') as f:
    f.write(function_summaries)
