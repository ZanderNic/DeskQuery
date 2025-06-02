# std-lib import
from typing import Optional, List, Dict, Tuple
from datetime import datetime, date, timedelta

# 3 party imports
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# projekt imports
from deskquery.data.dataset import Dataset
from deskquery.functions.core.policy import simulate_policy


def estimate_necessary_desks(
    data: Dataset,
    lag: int = 30,
    booking_type: str = "all",
    target_utilization: float = 0.8,
    weekly_growth_rate: float = None,
    weekly_absolute_growth: float = None,
    days_ahead: int = 365,
    policy: Dict = None,
    exceptions: Optional[Dict[int, Dict]] = None,
    random_assignments: Optional[List[Tuple[int, Dict]]] = None,
) -> dict[str, object]:
    """
    Estimates required number of desks to meet a target utilization. It can handle policies. If no policy
    is given it uses the attendance profile and a standard policy (no requirements). Either time series forecast is used or 
    the weekly growth rate / absolute growth. A policy is a dict of the following parameters 
    which are included in the policy, exceptions (if given) and random_assignments (if given):

        timeframe (str): Policy timeframe (currently only "week" is supported).
        fixed_days (Optional[List[str]]): Days that are always selected.
        choseable_days (Optional[List[str]]): Days from which a fixed number is chosen.
        number_choseable_days (Optional[int]): Number of days to pick from `choseable_days`.
        number_days (Optional[int]): Target total number of days.
        more_days_allowed (bool): If True, adds additional days based on attendance.

    Args:
        data (Dataset): The dataset containing booking data.
        lag (int): Number of days used to build the attendance profile (default: 30).
        booking_type (str): Either all, fixed (only fixed bookings) or variable (only variable bookings)
        target_utilization (float): Target average utilization (e.g., 0.8 for 80%).
        weekly_growth_rate (float, optional): Expected weekly multiplicative growth rate (e.g., 1.02 for +2% per week).
        weekly_absolute_growth (float, optional): Expected weekly absolute growth in employee count.
        days_ahead (int): Number of days into the future to simulate.
        policy (Dict): Base policy definition (see `simulate_policy` for structure).
        exceptions (Optional[Dict[int, Dict]]): Individual employee-specific exceptions to the policy.
        random_assignments (Optional[List[Tuple[int, Dict]]]): Random policy variants for specified number of employees.

    Returns:
        dict[str, object]: Contains the forecasted desk needs under key "data" and a "plotable" flag.
    """
    worker_timeseries = load_active_worker_timeseries(data, lag)[booking_type]
    current_worker_count = worker_timeseries.iloc[-1]
    num_weeks = days_ahead // 7

    if weekly_growth_rate is not None:
        worker_timeseries_forecast = np.array([
            current_worker_count * (weekly_growth_rate ** i)
            for i in range(num_weeks)
        ])
    elif weekly_absolute_growth is not None:
        worker_timeseries_forecast = np.array([
            current_worker_count + (weekly_absolute_growth * i)
            for i in range(num_weeks)
        ])
    else:
        worker_timeseries_forecast = forecast_timeseries(worker_timeseries, days_ahead)

    if not policy and (exceptions or random_assignments):
        raise ValueError("A policy is required when using exceptions or random assignments.")
    
    if not policy:
        policy = {"timeframe": "week"}

    simulation = simulate_policy(
        data=data,
        policy=policy,
        exceptions=exceptions,
        random_assignments=random_assignments,
        num_weeks=num_weeks
    )["data"]

    print(worker_timeseries)
    print(worker_timeseries_forecast)
    print(simulation)
    print(current_worker_count)
    print(target_utilization)
    desk_forecast = worker_timeseries_forecast * (np.max(simulation) / current_worker_count)  / target_utilization

    return {
        "data": np.array(desk_forecast),
        "plotable": True
    }
    

# not started yet
def simulate_room_closure(
    room_id: str, 
    reassign_strategy: str, 
    time_closed: Optional[str] = None, 
    data_for_forcast_start_date: Optional[datetime] = None, 
    data_for_forcast_end_date: Optional[datetime] = None
) -> None:
    """
    Simulates what happens if a room is closed.

    Args:
        room_id: Identifier of the room to close.
        reassign_strategy: Strategy to reassign affected bookings (e.g., 'random').
        time_closed: Timeframe of the closure.
        data_for_forcast_start_date: Data window start.
        data_for_forcast_end_date: Data window end.

    Returns:

    """
    pass



### Helper functions
def load_active_worker_timeseries(
        data: Dataset,
        time_window: int = 30
) -> Dict[str, pd.Series]:
    """
    Calculates the number of active workers at any given time. An active worker
    booked a desk in the last time_window days (standard 30).

    Args:
        time_window: Length of the time window.

    Returns:
        Dict of time series with date as index and the number of active workers.
    """
    data["blockedFrom"] = pd.to_datetime(data["blockedFrom"], errors="coerce")
    end_date = data["blockedFrom"].max().date()

    data["blockedUntil"] = data["blockedUntil"].astype(str)
    data.loc[data["blockedUntil"] == "unlimited", "blockedUntil"] = pd.Timestamp(end_date)
    data["blockedUntil"] = pd.to_datetime(data["blockedUntil"], errors="coerce")

    fixed = data[data["variableBooking"] == 0].copy()

    expanded_rows = []
    for _, row in fixed.iterrows():
        start = row["blockedFrom"].date()
        end = row["blockedUntil"].date()
        for day in pd.date_range(start=start, end=end, freq="D"):
            new_row = row.copy()
            new_row["blockedFrom"] = day
            new_row["blockedUntil"] = day
            expanded_rows.append(new_row)

    fixed_expanded = pd.DataFrame(expanded_rows)
    variable = data[data["variableBooking"] == 1].copy()

    data = pd.concat([variable, fixed_expanded], ignore_index=True)

    start_date = data["blockedFrom"].min().date()
    all_days = pd.date_range(start=start_date + timedelta(days=time_window - 1), end=end_date, freq="D").date

    def compute_timeseries(subset: pd.DataFrame) -> pd.Series:
        results = []
        for current_day in all_days:
            window_start = current_day - timedelta(days=time_window - 1)
            mask = (subset["blockedFrom"].dt.date >= window_start) & (subset["blockedFrom"].dt.date <= current_day)
            active_users = subset.loc[mask, "userId"].nunique()
            results.append((current_day, active_users))
        return pd.Series(dict(results), name="active_worker_count")

    timeseries_all = compute_timeseries(data)
    timeseries_fixed = compute_timeseries(data[data["variableBooking"] == 0])
    timeseries_variable = compute_timeseries(data[data["variableBooking"] == 1])

    return {
        "all": timeseries_all,
        "fixed": timeseries_fixed,
        "variable": timeseries_variable
    }


# Just for testing now. Can be removed later
def plot_timeseries_with_forecast(
        historical: pd.Series, 
        forecast: pd.Series = None, 
        title: str = "Time Series with Prediction"
        ):
    plt.figure(figsize=(12, 6))
    plt.plot(historical.index, historical.values, label="Historical", color="blue")
    if forecast is not None:
        plt.plot(forecast.index, forecast.values, label="Prediction", color="red")
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def forecast_timeseries(
        ts: pd.Series, 
        days_ahead: int = 365, 
        method: str = "linear", 
        without_history: bool = True
) -> pd.Series:
    """
    Forecasts a time series with a model.

        Estimates required number of desks to meet a target utilization.

    Args:
        ts: Time series which is used for forecast.
        days_ahead: How many days in the future are predicted.
        method: Method of forecasting.
        without_history: If set returns only the forecast without the given ts.

    Returns:
        The forecast time series (combined with the orginial time series)
    """
    ts = ts.copy()
    ts.index = pd.to_datetime(ts.index)
    ts = ts.asfreq("D")
    
    if method == "linear":
        x = np.arange(len(ts)).reshape(-1, 1)
        y = ts.values
        model = LinearRegression()
        model.fit(x, y)
        future_x = np.arange(len(ts), len(ts) + days_ahead).reshape(-1, 1)
        forecast = model.predict(future_x).squeeze()
    
    elif method == "ets":
        model = ExponentialSmoothing(ts, trend="add", seasonal=None)
        fitted = model.fit()
        forecast = fitted.forecast(days_ahead)
    
    else:
        raise ValueError(f"Method unknown: {method}. Known models: linear, ets")
    
    future_dates = pd.date_range(ts.index[-1] + pd.Timedelta(days=1), periods=days_ahead)
    forecast_series = pd.Series(forecast, index=future_dates, name="forecast")
    
    if without_history:
        return forecast_series
    ts.name = "historical"
    return pd.concat([ts, forecast_series], axis=0)


if __name__ == "__main__":
    from pprint import pprint
    from deskquery.data.dataset import create_dataset

    dataset = create_dataset()

    ########## Test estimate_necessary_desks with weekly growth rate ################################################
    print("=== Estimate necessary desks with weekly growth rate ===")
    return_dict = estimate_necessary_desks(
        data=dataset,
        weekly_growth_rate=1.02
    )
    pprint(return_dict["data"])
    print()

    ########## Test estimate_necessary_desks with weekly absolute growth ################################################
    print("=== Estimate necessary desks with weekly absolute growth ===")
    return_dict = estimate_necessary_desks(
        data=dataset,
        weekly_absolute_growth=1.2
    )
    pprint(return_dict["data"])
    print()

    ########## Test estimate_necessary_desks with time series forecast ################################################
    print("=== Estimate necessary desks with time series forecast ===")
    return_dict = estimate_necessary_desks(
        data=dataset
    )
    pprint(return_dict["data"])
    print()

    ########## Test estimate_necessary_desks with policy ################################################
    policy = {
        "fixed_days":["Di"],
        "choseable_days":["Mi", "Do"],
        "number_choseable_days":1,
        "number_days":3,
        "more_days_allowed":True
    }

    exceptions = {
        4: {'fixed_days': ["Fr"], 'number_days': 4, 'more_days_allowed': True},
        14: {'fixed_days': ["Fr"], 'number_days': 4, 'more_days_allowed': True}
    }

    random_assignments = [
        (10, {'number_days': 1, 'more_days_allowed': False})
    ]

    print("=== Estimate necessary desks with policy ===")
    return_dict = estimate_necessary_desks(
        data=dataset,
        policy=policy,
        exceptions=exceptions,
        random_assignments=random_assignments
    )
    pprint(return_dict["data"])
    print()
