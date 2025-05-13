from deskquery.functions.core.plot import *
from deskquery.functions.core.policy import *
from deskquery.functions.core.utilization import * 
from deskquery.functions.core.employee import *
from deskquery.functions.core.forecasting import *
import inspect


function_registry = {
    # Utilization
    "get_utilization": get_utilization,
    "get_over_under_utilized_desks": get_over_under_utilized_desks,
    "get_daily_utilization_stats": get_daily_utilization_stats,
    "get_days_above_bellow_threshold": get_days_above_bellow_threshold,
    "detect_utilization_anomalies": detect_utilization_anomalies,

    # Policy
    "simulate_policy": simulate_policy,
    "detect_policy_violations": detect_policy_violations,
    "suggest_balanced_utilization_policy": suggest_balanced_utilization_policy,
    "compare_utilization_before_after_policy": compare_utilization_before_after_policy,

    # Employee behavior
    "get_avg_booking_per_employee": get_avg_booking_per_employee,
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
 
def create_function_summaries(function_registry):
    function_summaries = ""

    for name, func in function_registry.items():
        definition = inspect.getsource(func).strip().splitlines()
        # we only want the declaration not the whole function code. so just use the first line
        declaration = definition[0]
        function_summaries += declaration + "\n"
        docstring = inspect.getdoc(func)
        function_summaries += docstring + "\n"

    return function_summaries

function_summaries = create_function_summaries(function_registry)