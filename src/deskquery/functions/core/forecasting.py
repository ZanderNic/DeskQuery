# std-lib import
from typing import Optional, List, Dict, Tuple
from datetime import timedelta
from deskquery.functions.types import FunctionData

# 3 party imports
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.statespace.sarimax import SARIMAX

# projekt imports
from deskquery.data.dataset import Dataset
from deskquery.functions.core.policy import simulate_policy
from deskquery.functions.types import FunctionRegistryExpectedFormat, PlotForFunction
from deskquery.functions.core.helper.plot_helper import generate_lineplot


def forecast_employees(
    data: Dataset,
    lag: Optional[int] = 90,
    booking_type: Optional[str] = "all",
    weekly_growth_rate: Optional[float] = None,
    weekly_absolute_growth: Optional[float] = None,
    forecast_model: Optional[str] = "linear",
    weeks_ahead: Optional[int] = 52,
    plotable: bool = True
) -> FunctionRegistryExpectedFormat:
    """
    Forecasts the number of employees with different models such as linear or sarima. 
    Furthermore, this function can handle fixed weekly growth rates and fixed weekly absolute growth. 
    It gets the worker time series and then forecasts future employee numbers.

    Args:
        data (Dataset): 
            The dataset containing booking data.
        lag (int, optional): 
            Number of days used to build the attendance profile. Defaults to 90.
        booking_type (str, optional): 
            Either 'all', 'fixed' (only fixed bookings) or 'variable' (only variable bookings).
            Defaults to all bookings being used if none is given.
        weekly_growth_rate (float, optional): 
            Expected weekly multiplicative growth rate (e.g., 1.02 for +2% per week).
            Defaults to `None`, meaning no growth rate is applied.
        weekly_absolute_growth (float, optional): 
            Expected weekly absolute growth in employee count.
            Defaults to `None`, meaning no absolute growth is applied.
        forecast_model (str, optional): 
            Model used to forecast time series if weekly_growth_rate and 
            weekly_absolute_growth are not given. This can be either "linear" for 
            linear regression or "sarima" for seasonal moving average regression.
            Defaults to "linear".
        weeks_ahead (int, optional): 
            Number of weeks into the future to simulate. Defaults to 52 weeks.
        plotable (bool): 
            If called from another function, set to False. Defaults to True, meaning
            the function will return a plotable result.

    Returns:
        FunctionRegistryExpectedFormat: 
            - If `plotable` is True, it returns a FunctionRegistryExpectedFormat object
              containing the worker history and forecast series, as well as a plot.
        Tuple[int, pd.Series]:
            - If `plotable` is False, it returns a tuple with the current worker count
              and the forecasted worker count series.
    """
    # set default values if applicable
    if not lag or lag <= 0:
        lag = 90
    if not booking_type or booking_type not in ["all", "fixed", "variable"]:
        booking_type = 'all'
    if not forecast_model or forecast_model not in ["linear", "sarima"]:
        forecast_model = "linear"
    if not weeks_ahead or weeks_ahead <= 0:
        weeks_ahead = 52
    if not plotable:
        plotable = True

    worker_history_series = load_active_worker_timeseries(data, lag)[booking_type]
    current_worker_count = worker_history_series.iloc[-1]

    start_week = worker_history_series.index[-1] + pd.Timedelta(weeks=1)
    forecast_index = pd.date_range(start=start_week, periods=weeks_ahead, freq="W-MON")

    if weekly_growth_rate and weekly_absolute_growth:
        raise ValueError("Either use weekly_growth_rate or weekly_absolute_growth. If None is given the forecast is done with the forecast_model")

    if weekly_growth_rate is not None:
        worker_forecast = np.array([
            current_worker_count * (weekly_growth_rate ** i)
            for i in range(weeks_ahead)
        ])
    elif weekly_absolute_growth is not None:
        worker_forecast = np.array([
            current_worker_count + (weekly_absolute_growth * i)
            for i in range(weeks_ahead)
        ])
    else:
        if forecast_model == "sarima":
            model = SARIMAX(worker_history_series, order=(1, 1, 1), seasonal_order=(1, 1, 1, 52), enforce_stationarity=False, enforce_invertibility=False)
            results = model.fit(disp=False)
            forecast = results.forecast(steps=weeks_ahead)
            worker_forecast = forecast.values

        else:
            forecast = forecast_timeseries(worker_history_series, weeks_ahead, forecast_model)
            if isinstance(forecast, pd.Series):
                forecast = forecast.resample("W-MON").mean().iloc[:weeks_ahead].values
            worker_forecast = forecast

    worker_forecast_series = pd.Series(worker_forecast, index=forecast_index, name="Worker forecast")

    if plotable:
        num_desks = data["deskId"].nunique()
        combined_index = worker_history_series.index.union(worker_forecast_series.index)
        num_desks_series = pd.Series(num_desks, index=combined_index, name="number_of_desks")

        final_data = FunctionData({
            "worker_history": worker_history_series.to_dict(),
            "worker_forecast": worker_forecast_series.to_dict(),
            "number_of_desks": num_desks_series.to_dict()
        })

        plot = PlotForFunction(
            default_plot=generate_lineplot(
                data=final_data,
                title=f"Number of employees with {booking_type} bookings",
                xaxis_title="Date",
                yaxis_title="Number of employees"
            ),
            available_plots=[generate_lineplot]
        )

        return FunctionRegistryExpectedFormat(data=final_data, plot=plot)
    
    return current_worker_count, worker_forecast_series


def estimate_necessary_desks(
    data: Dataset,
    policy: Optional[Dict] = None,
    exceptions: Optional[Dict[int, Dict]] = None,
    random_assignments: Optional[List[Tuple[int, Dict]]] = None,
    lag: Optional[int] = 90,
    booking_type: Optional[str] = "all",
    weekly_growth_rate: Optional[float] = None,
    weekly_absolute_growth: Optional[float] = None,
    forecast_model: Optional[str] = "linear",
    weeks_ahead: Optional[int] = 52,
    target_utilization: Optional[float] = 1.0,
) -> FunctionRegistryExpectedFormat:
    """
    Estimates required number of desks to meet a target utilization. It can handle policies. 
    If no policy is given, it uses the attendance profile and a standard policy (no requirements).
    Either time series forecast is used or the weekly growth rate / absolute growth.
    A policy is a dict of the following parameters which are included in the policy, 
    exceptions (if given) and random_assignments (if given):

    policy = {
        timeframe (str): Policy timeframe (currently only "week" is supported);
        fixed_days (List[str], optional): Days that are always selected;
        choseable_days (List[str], optional): Days from which a fixed number is chosen;
        number_choseable_days (int, optional): Number of days to pick from `choseable_days`;
        number_days (int, optional): Target total number of days;
        more_days_allowed (bool): If True, adds additional days based on attendance;
    }

    Args:
        data (Dataset): 
            The dataset containing booking data.
        policy (Dict): 
            Base policy definition from above. If not given, the policy {"timeframe": "week"} is used.
        exceptions (Dict[int, Dict], optional): 
            Targeted special rules for certain employee IDs. Defaults to `None`,
            meaning the default policy is applied to all employees.
        random_assignments (List[Tuple[int, Dict]], optional):
            List of tuples (number_of_employees, policy dict) for random policy
            variant assignments for a specified number of employees.
            Defaults to `None`, meaning no random assignments are made.
        lag (int, optional): 
            Number of days used to build the attendance profile. Defaults to 90.
        booking_type (str, optional): 
            Either 'all', 'fixed' (only fixed bookings) or 'variable' (only variable bookings).
            Defaults to all bookings being used if none is given.
        weekly_growth_rate (float, optional): 
            Expected weekly multiplicative growth rate (e.g., 1.02 for +2% per week).
            Defaults to `None`, meaning no growth rate is applied.
        weekly_absolute_growth (float, optional): 
            Expected weekly absolute growth in employee count.
            Defaults to `None`, meaning no absolute growth is applied.
        forecast_model (str): 
            Model used to forecast time series if weekly_growth_rate and 
            weekly_absolute_growth are not given. This can be either "linear" for 
            linear regression or "sarima" for seasonal moving average regression.
            Defaults to "linear".
        weeks_ahead (int, optional): 
            Number of weeks into the future to simulate. Defaults to 52 weeks.
        target_utilization (float, optional): 
            Target average utilization (e.g., 0.8 for 80%). Defaults to 1.0 (100% utilization).

    Returns:
        FunctionRegistryExpectedFormat: 
            A FunctionRegistryExpectedFormat object containing the necessary desks 
            forecast and number of desks as well as a plot.
    """
    # set default values if applicable
    if not lag or lag <= 0:
        lag = 90
    if not booking_type or booking_type not in ["all", "fixed", "variable"]:
        booking_type = 'all'
    if not forecast_model or forecast_model not in ["linear", "sarima"]:
        forecast_model = "linear"
    if not weeks_ahead or weeks_ahead <= 0:
        weeks_ahead = 52
    if not target_utilization or target_utilization < 0.0:
        target_utilization = 1.0

    current_worker_count, worker_forecast_series = forecast_employees(data, lag, booking_type, weekly_growth_rate, weekly_absolute_growth, forecast_model, weeks_ahead, False)

    worker_forecast = worker_forecast_series.values

    if not policy and (exceptions or random_assignments):
        raise ValueError("A policy is required when using exceptions or random assignments.")
    
    if not policy:
        policy = {"timeframe": "week"}

    simulation = simulate_policy(
        data=data,
        policy=policy,
        exceptions=exceptions,
        random_assignments=random_assignments,
        num_weeks=100,
        plotable=False
    ).data

    scaling_factor = np.max(simulation) / current_worker_count
    desk_forecast = worker_forecast * scaling_factor / target_utilization

    desk_forecast_series = pd.Series(desk_forecast, index=worker_forecast_series.index, name="necessary_desks")

    num_desks = data["deskId"].nunique()
    num_desks_series = pd.Series(num_desks, index=worker_forecast_series.index, name="number_of_desks")

    final_data = FunctionData({
        "desk_forecast": desk_forecast_series.to_dict(),
        "number_of_desks": num_desks_series.to_dict()
    })

    plot = PlotForFunction(
        default_plot=generate_lineplot(
            data=final_data,
            title=f"Necessary desks for {booking_type} bookings",
            xaxis_title="Date",
            yaxis_title="Necessary desks"
        ),
        available_plots=[generate_lineplot]
    )

    return FunctionRegistryExpectedFormat(data=final_data, plot=plot)
    

####### Helpers ###########################################################################################################################################################################

def load_active_worker_timeseries(
    data: Dataset,
    time_window: int = 90
) -> Dict[str, pd.Series]:
    """
    Calculates the number of active workers at any given time. An active worker
    booked a desk in the last time_window days (standard 90).

    Args:
        time_window: Length of the time window.

    Returns:
        Dict of time series with date as index and the number of active workers.
    """
    data["blockedFrom"] = pd.to_datetime(data["blockedFrom"], errors="coerce")

    variable = data[data["variableBooking"] == 1].copy()
    end_date = variable["blockedFrom"].max().date()

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
    data = pd.concat([variable, fixed_expanded], ignore_index=True)

    start_date = data["blockedFrom"].min().date()
    all_weeks = pd.date_range(start=start_date + timedelta(days=time_window - 1), end=end_date, freq="W-MON").date

    def compute_timeseries(subset: pd.DataFrame) -> pd.Series:
        results = []
        for week_start in all_weeks:
            window_start = week_start - timedelta(days=time_window - 1)
            mask = (subset["blockedFrom"].dt.date >= window_start) & (subset["blockedFrom"].dt.date <= week_start)
            active_users = subset.loc[mask, "userId"].nunique()
            results.append((week_start, active_users))
        return pd.Series(dict(results), name="active_worker_count")

    return {
        "all": compute_timeseries(data),
        "fixed": compute_timeseries(data[data["variableBooking"] == 0]),
        "variable": compute_timeseries(data[data["variableBooking"] == 1])
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
    periods_ahead: int = 52, 
    method: str = "linear", 
    without_history: bool = True
) -> pd.Series:
    """
    Forecasts a time series with a model.

    Args:
        ts: Time series to use for forecasting.
        periods_ahead: Number of periods (weeks or days) to forecast.
        method: Method of forecasting: "linear" or "ets".
        without_history: If True, returns only the forecast; otherwise includes history.

    Returns:
        Forecast time series as pd.Series.
    """
    ts = ts.copy()
    ts.index = pd.to_datetime(ts.index)

    freq = pd.infer_freq(ts.index)
    if freq is None:
        raise ValueError("Cannot infer frequency of time series.")

    ts = ts.asfreq(freq)

    if method == "linear":
        x = np.arange(len(ts)).reshape(-1, 1)
        y = ts.values
        model = LinearRegression()
        model.fit(x, y)
        future_x = np.arange(len(ts), len(ts) + periods_ahead).reshape(-1, 1)
        forecast = model.predict(future_x).squeeze()
    
    elif method == "ets":
        model = ExponentialSmoothing(ts, trend="add", seasonal=None)
        fitted = model.fit()
        forecast = fitted.forecast(periods_ahead)
    
    else:
        raise ValueError(f"Unknown method '{method}'. Use 'linear' or 'ets'.")

    future_dates = pd.date_range(
        start=ts.index[-1] + pd.tseries.frequencies.to_offset(freq),
        periods=periods_ahead,
        freq=freq
    )

    forecast_series = pd.Series(forecast, index=future_dates, name="forecast")
    if without_history:
        return forecast_series
    ts.name = "historical"
    return pd.concat([ts, forecast_series])


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
