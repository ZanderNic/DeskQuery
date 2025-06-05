# std-lib imports
from datetime import datetime
import unittest

# 3 party imports
from parameterized import parameterized

# project imports
from deskquery.functions.core.employee import *
from deskquery.data.dataset import *
""""
-> Funktionsweise der einelnen Funktionen testen 
-> Funktionsausgabe mit passenden Paramtern gegenüber den Richitgen Ergebniss

"""

class BasisTests(unittest.TestCase):
    def setUp(self):
        self.dataset = create_dataset()

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
  

if __name__ == "__main__":
    unittest.main()
