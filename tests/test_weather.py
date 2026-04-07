import unittest
from unittest.mock import patch, MagicMock
import datetime
import time
import requests
from app.weather import (
    _is_valid_coords,
    _apply_rate_limit,
    _validate_response_data,
    _format_date_br,
    _format_day_name,
    get_weather_data,
    get_5_day_forecast,
    get_cached_weather_data,
    cache,
    last_request_time,
    CACHE_EXPIRATION_SECONDS
)


class TestWeatherFunctions(unittest.TestCase):

    def test_is_valid_coords_valid(self):
        self.assertTrue(_is_valid_coords(0, 0))
        self.assertTrue(_is_valid_coords(90, 180))
        self.assertTrue(_is_valid_coords(-90, -180))
        self.assertTrue(_is_valid_coords(45.5, -122.3))

    def test_is_valid_coords_invalid(self):
        self.assertFalse(_is_valid_coords(91, 0))
        self.assertFalse(_is_valid_coords(0, 181))
        self.assertFalse(_is_valid_coords(-91, 0))
        self.assertFalse(_is_valid_coords(0, -181))
        self.assertFalse(_is_valid_coords("45", 0))
        self.assertFalse(_is_valid_coords(45, "0"))

    @patch('app.weather.time.sleep')
    @patch('app.weather.time.time')
    def test_apply_rate_limit(self, mock_time, mock_sleep):
        # Reset global
        import app.weather
        app.weather.last_request_time = 1.0  # Set to recent time
        mock_time.return_value = 1.2  # Elapsed = 0.2 < 1.0
        _apply_rate_limit()
        mock_sleep.assert_called_once_with(0.8)  # RATE_LIMIT_DELAY - elapsed

    def test_validate_response_data_valid(self):
        data = {"key1": "value1", "key2": "value2"}
        required = ["key1", "key2"]
        self.assertTrue(_validate_response_data(data, required))

    def test_validate_response_data_invalid(self):
        data = {"key1": "value1"}
        required = ["key1", "key2"]
        self.assertFalse(_validate_response_data(data, required))

    def test_format_date_br_valid(self):
        result = _format_date_br("2023-10-15")
        self.assertEqual(result, "15/10/2023")

    def test_format_date_br_invalid(self):
        result = _format_date_br("invalid")
        self.assertEqual(result, "invalid")

    def test_format_day_name_valid(self):
        # Assuming 2023-10-15 is a Sunday (weekday 6)
        result = _format_day_name("2023-10-15")
        self.assertEqual(result, "Dom")

    def test_format_day_name_invalid(self):
        result = _format_day_name("invalid")
        self.assertEqual(result, "invalid")

    @patch('app.weather.session.get')
    def test_get_weather_data_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "current": {
                "temperature_2m": 25.7,
                "windspeed_10m": 10.5,
                "relative_humidity_2m": 60.2,
                "precipitation": 0.0
            }
        }
        mock_get.return_value = mock_response

        result = get_weather_data(45.0, -122.0)
        expected = {
            "temperature": 26,
            "windspeed": 10.5,
            "humidity": 60,
            "precipitation": 0.0
        }
        self.assertEqual(result, expected)

    @patch('app.weather.session.get')
    def test_get_weather_data_invalid_coords(self, mock_get):
        result = get_weather_data(91, 0)
        self.assertIsNone(result)
        mock_get.assert_not_called()

    @patch('app.weather.session.get')
    def test_get_weather_data_request_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("Request failed")
        result = get_weather_data(45.0, -122.0)
        self.assertIsNone(result)

    @patch('app.weather.session.get')
    def test_get_weather_data_invalid_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"no_current": {}}
        mock_get.return_value = mock_response

        result = get_weather_data(45.0, -122.0)
        self.assertIsNone(result)

    @patch('app.weather.session.get')
    def test_get_5_day_forecast_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "daily": {
                "time": ["2023-10-15", "2023-10-16", "2023-10-17", "2023-10-18", "2023-10-19", "2023-10-20"],
                "temperature_2m_max": [25, 26, 27, 28, 29, 30],
                "temperature_2m_min": [15, 16, 17, 18, 19, 20],
                "precipitation_sum": [0, 1, 2, 3, 4, 5],
                "windspeed_10m_max": [10, 11, 12, 13, 14, 15],
                "relative_humidity_2m_mean": [50, 51, 52, 53, 54, 55]
            }
        }
        mock_get.return_value = mock_response

        result = get_5_day_forecast(45.0, -122.0)
        self.assertEqual(len(result), 5)
        # Check first item (skipping today)
        self.assertIn("date", result[0])
        self.assertIn("temp_max", result[0])

    @patch('app.weather.session.get')
    def test_get_5_day_forecast_invalid_coords(self, mock_get):
        result = get_5_day_forecast(91, 0)
        self.assertIsNone(result)
        mock_get.assert_not_called()

    @patch('app.weather.get_weather_data')
    def test_get_cached_weather_data_hit(self, mock_get_weather):
        # Clear cache
        cache.clear()
        key = (45.0, -122.0)
        now = datetime.datetime.now()
        cache[key] = {"data": {"temp": 25}, "timestamp": now}

        result = get_cached_weather_data(45.0, -122.0)
        self.assertEqual(result, {"temp": 25})
        mock_get_weather.assert_not_called()

    @patch('app.weather.get_weather_data')
    def test_get_cached_weather_data_miss(self, mock_get_weather):
        cache.clear()
        mock_get_weather.return_value = {"temp": 25}

        result = get_cached_weather_data(45.0, -122.0)
        self.assertEqual(result, {"temp": 25})
        mock_get_weather.assert_called_once_with(45.0, -122.0)

    @patch('app.weather.get_weather_data')
    def test_get_cached_weather_data_expired(self, mock_get_weather):
        cache.clear()
        key = (45.0, -122.0)
        old_time = datetime.datetime.now() - datetime.timedelta(seconds=CACHE_EXPIRATION_SECONDS + 1)
        cache[key] = {"data": {"temp": 25}, "timestamp": old_time}
        mock_get_weather.return_value = {"temp": 26}

        result = get_cached_weather_data(45.0, -122.0)
        self.assertEqual(result, {"temp": 26})
        mock_get_weather.assert_called_once()


if __name__ == '__main__':
    unittest.main()