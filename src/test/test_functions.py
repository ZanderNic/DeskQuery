# std-lib imports
from datetime import datetime
import unittest

# 3 party imports
from parameterized import parameterized

# project imports
from deskquery.functions.core.employee import get_avg_employee_bookings, get_booking_repeat_pattern, get_booking_clusters, get_co_booking_frequencies
from deskquery.functions.core.forecasting import forecast_employees, estimate_necessary_desks
from deskquery.functions.core.policy import simulate_policy, detect_policy_violations
from deskquery.data.dataset import *


class BasisTests(unittest.TestCase):
    def setUp(self):
        self.dataset = create_dataset(path="src\deskquery\data\OpTisch_anonymisiert.xlsx")

class TestGetAvgEmployeeBookings(BasisTests):
    @parameterized.expand([
        ("names_month_mean", {
                            "user_names": ["Alice"], 
                            "granularity": "month",
                            "return_total_mean": True,
                            "start_date": datetime.strptime("2022.12.19", "%Y.%m.%d"),
                            "end_date": datetime.strptime("2025.05.20", "%Y.%m.%d")
                            }),
        ("ids_week_double", {
                            "user_ids": [1, 2],
                            "granularity": "week",
                            "include_double_bookings": True,
                            "include_fixed": False
                            }),
        ("employees_day",  {
                            "num_employees": 10,
                            "granularity": "day",
                            "weekdays": ["tuesday", "wednesday", "thursday", "friday"],
                            "return_user_names": False
                            }),
    ])
    def test_get_avg_employee_bookings(self, name, kwargs):
        result = get_avg_employee_bookings(self.dataset, **kwargs)
        self.assertIsNotNone(result)

class TestGetBookingRepeatPattern(BasisTests):
    @parameterized.expand([
        ("default_case", {
                        "user_names": ["Alice", "Bob"]
                        }),
        ("custom_weekdays_and_desk", {
                        "user_ids": [1], "most_used_desk": 2,
                        "weekdays": ["monday", "wednesday"]
                        }),
        ("with_date_range", {
                        "start_date": datetime.strptime("2023.01.01", "%Y.%m.%d"),
                        "end_date": datetime.strptime("2023.12.31", "%Y.%m.%d"),
                        "include_fixed": False
                        }),
        ("single_user_id", {
                        "user_ids": 5
                        }),
    ])
    def test_get_booking_repeat_pattern(self, name, kwargs):
        result = get_booking_repeat_pattern(self.dataset, **kwargs)
        self.assertIsNotNone(result["data"])

class TestGetBookingClusters(BasisTests):
    @parameterized.expand([
        ("default_case", {
                        "co_booking_count_min": 4
                        }),
        ("custom_weekdays", {
                        "user_ids": [1],
                        "weekdays": ["monday", "wednesday"]
                        }),
        ("with_date_range", {
                        "start_date": datetime.strptime("2023.01.01", "%Y.%m.%d"),
                        "end_date": datetime.strptime("2023.12.31", "%Y.%m.%d"),
                        "include_fixed": False
                        }),
        ("single_user_id", {
                        "user_ids": [5]  
                        }),
    ])
    def test_get_booking_clusters(self, name, kwargs):
        result = get_booking_clusters(self.dataset, **kwargs)
        self.assertIsNotNone(result)
    
class TestGetCoBookingFrequencies(BasisTests):
    @parameterized.expand([
        ("default_case", {}),
        ("custom_min_shared_days", {
                        "min_shared_days": 10
                        }),
        ("same_room_only", {
                        "same_room_only": True
                        }),
        ("custom_weekdays", {
                        "weekdays": ["monday", "wednesday"]
                        }),
        ("with_date_range", {
                        "start_date": datetime.strptime("2023.01.01", "%Y.%m.%d"),
                        "end_date": datetime.strptime("2023.12.31", "%Y.%m.%d")
                        }),
        ("exclude_fixed", {
                        "include_fixed": False
                        }),
    ])
    def test_get_co_booking_frequencies(self, name, kwargs):
        result = get_co_booking_frequencies(self.dataset, **kwargs)
        self.assertIsNotNone(result)
  
class TestEstimateNecessaryDesks(BasisTests):
    @parameterized.expand([
        ("default_case", {}),
        ("with_weekly_growth", {
                        "weekly_growth_rate": 1.02
                        }),
        ("with_growth", {
                        "weekly_absolute_growth": 1.2
                        }),
        ("with_policy_and_exceptions", {
                        "policy": {
                            "fixed_days": ["Di"],
                            "choseable_days": ["Mi", "Do"],
                            "number_choseable_days": 1,
                            "number_days": 3,
                            "more_days_allowed": True
                        },
                        "exceptions": {
                            4: {'fixed_days': ["Fr"], 'number_days': 4, 'more_days_allowed': True},
                            14: {'fixed_days': ["Fr"], 'number_days': 4, 'more_days_allowed': True}
                        },
                        "random_assignments": [
                            (10, {'number_days': 1, 'more_days_allowed': False})
                        ]
                    })
    ])
    def test_estimate(self, name, kwargs):
        result = estimate_necessary_desks(data=self.dataset, **kwargs)
        self.assertIsNotNone(result["data"])

class TestForcastEmployees(BasisTests):
    @parameterized.expand([
        ("default_case", {}),
        ("with_weekly_growth_rate", {
                                    "weekly_growth_rate": 1.05
                                    }),
        ("with_weekly_absolute_growth", {
                                    "weekly_absolute_growth": 2.0
                                    }),
        ("with_different_forecast_model", {
                                    "forecast_model": "ets"
                                    }),
        ("with_lag_and_weeks_ahead", {
                                    "lag": 60,
                                    "weeks_ahead": 26,
                                    "plotable": False
                                    }),
    ])
    def test_estimate(self, name, kwargs):
        result = forecast_employees(data=self.dataset, **kwargs)
        self.assertIsNotNone(result["data"])

class TestSimulatePolicy(BasisTests):
    @parameterized.expand([
        ("default_policy", {
                        "policy": {
                            "fixed_days": ["Di"],
                            "choseable_days": ["Mi", "Do"],
                            "number_choseable_days": 1,
                            "number_days": 3,
                            "more_days_allowed": True
                            }
                        }),
        ("with_exceptions", {
                        "policy": {
                            "fixed_days": ["Di"],
                            "choseable_days": ["Mi", "Do"],
                            "number_choseable_days": 1,
                            "number_days": 3,
                            "more_days_allowed": True
                            },
                        "exceptions": {
                            4: {'fixed_days': ["Fr"], 'number_days': 4, 'more_days_allowed': True},
                            14: {'fixed_days': ["Fr"], 'number_days': 4, 'more_days_allowed': True}
                            }
                        }),
        ("with_random_assignments", {
                                "policy": {
                                    "fixed_days": ["Di"],
                                    "choseable_days": ["Mi", "Do"],
                                    "number_choseable_days": 1,
                                    "number_days": 3,
                                    "more_days_allowed": True
                                },
                                "random_assignments": [
                                    (10, {'number_days': 1, 'more_days_allowed': False})
                                    ]
                                }),
    ])

    def test_estimate(self, name, kwargs):
        result = simulate_policy(data=self.dataset, **kwargs)
        self.assertIsNotNone(result["data"])


class TestDetectPolicyViolations(BasisTests):
    @parameterized.expand([
        (
            "default_policy",  # Testname
            {
                "policy": {
                    "fixed_days": ["Di"],
                    "choseable_days": ["Mi", "Do"],
                    "number_choseable_days": 1,
                    "number_days": 3,
                    "more_days_allowed": True
                }
            }
        ),
        (
            "with_exceptions",
            {
                "policy": {
                    "fixed_days": ["Di"],
                    "choseable_days": ["Mi", "Do"],
                    "number_choseable_days": 1,
                    "number_days": 3,
                    "more_days_allowed": True
                },
                "exceptions": {
                    5: {"fixed_days": ["Fr"], "number_days": 4, "more_days_allowed": True}
                }
            }
        ),
        (
            "with_random_assignments",
            {
                "policy": {
                    "fixed_days": ["Di"],
                    "choseable_days": ["Mi", "Do"],
                    "number_choseable_days": 1,
                    "number_days": 3,
                    "more_days_allowed": True
                },
                "random_assignments": [
                    (10, {"number_days": 2, "more_days_allowed": False})
                ]
            }
        ),
        (
            "custom_weekdays_and_range",
            {
                "policy": {
                    "fixed_days": ["Di"],
                    "choseable_days": ["Mi"],
                    "number_choseable_days": 1,
                    "number_days": 2,
                    "more_days_allowed": False
                },
                "weekdays": ["Mo", "Di", "Mi"],
                "start_date": datetime(2024, 6, 3),
                "end_date": datetime(2024, 6, 30),
                "only_stats": True
            }
        )
    ])
    def test_detect_policy_violations(self, name, kwargs):
        result = detect_policy_violations(data=self.dataset, **kwargs)
        self.assertIsNotNone(result)
        self.assertIn("data", result)


if __name__ == "__main__":
    unittest.main()
