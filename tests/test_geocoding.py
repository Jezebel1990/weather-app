import unittest
from unittest.mock import patch, MagicMock
import time
import requests
from app.geocoding import (
    _is_valid_city_name,
    _is_valid_coordinates,
    _apply_rate_limit,
    get_coordinates,
    last_request_time
)


class TestGeocodingFunctions(unittest.TestCase):

    def test_is_valid_city_name_valid(self):
        self.assertTrue(_is_valid_city_name("São Paulo"))
        self.assertTrue(_is_valid_city_name("New York"))
        self.assertTrue(_is_valid_city_name("London"))
        self.assertTrue(_is_valid_city_name("Paris-France"))
        self.assertTrue(_is_valid_city_name("Cidade com espaços"))

    def test_is_valid_city_name_invalid(self):
        self.assertFalse(_is_valid_city_name(""))
        self.assertFalse(_is_valid_city_name("   "))
        self.assertFalse(_is_valid_city_name("a" * 101))  # Too long
        self.assertFalse(_is_valid_city_name("Cidade@Inválida!"))
        self.assertFalse(_is_valid_city_name(None))
        self.assertFalse(_is_valid_city_name(123))

    def test_is_valid_coordinates_valid(self):
        self.assertTrue(_is_valid_coordinates(0, 0))
        self.assertTrue(_is_valid_coordinates(90, 180))
        self.assertTrue(_is_valid_coordinates(-90, -180))
        self.assertTrue(_is_valid_coordinates(45.5, -122.3))

    def test_is_valid_coordinates_invalid(self):
        self.assertFalse(_is_valid_coordinates(91, 0))
        self.assertFalse(_is_valid_coordinates(0, 181))
        self.assertFalse(_is_valid_coordinates(-91, 0))
        self.assertFalse(_is_valid_coordinates(0, -181))
        self.assertFalse(_is_valid_coordinates("45", 0))
        self.assertFalse(_is_valid_coordinates(45, "0"))

    @patch('app.geocoding.time.sleep')
    @patch('app.geocoding.time.time')
    def test_apply_rate_limit(self, mock_time, mock_sleep):
        # Reset global
        import app.geocoding
        app.geocoding.last_request_time = 1.0  # Set to recent time
        mock_time.return_value = 1.2  # Elapsed = 0.2 < 0.5
        _apply_rate_limit()
        mock_sleep.assert_called_once()
        args, kwargs = mock_sleep.call_args
        self.assertAlmostEqual(args[0], 0.3, places=5)

    @patch('app.geocoding.requests.get')
    def test_get_coordinates_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "results": [
                {
                    "latitude": -23.5505,
                    "longitude": -46.6333
                }
            ]
        }
        mock_get.return_value = mock_response

        lat, lon = get_coordinates("São Paulo")
        self.assertEqual(lat, -23.5505)
        self.assertEqual(lon, -46.6333)

    @patch('app.geocoding.requests.get')
    def test_get_coordinates_invalid_city(self, mock_get):
        lat, lon = get_coordinates("Cidade@Inválida!")
        self.assertIsNone(lat)
        self.assertIsNone(lon)
        mock_get.assert_not_called()

    @patch('app.geocoding.requests.get')
    def test_get_coordinates_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        lat, lon = get_coordinates("Cidade Inexistente")
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    @patch('app.geocoding.requests.get')
    def test_get_coordinates_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")
        lat, lon = get_coordinates("São Paulo")
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    @patch('app.geocoding.requests.get')
    def test_get_coordinates_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError("404")
        http_error.response = mock_response
        mock_get.side_effect = http_error

        lat, lon = get_coordinates("São Paulo")
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    @patch('app.geocoding.requests.get')
    def test_get_coordinates_request_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        lat, lon = get_coordinates("São Paulo")
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    @patch('app.geocoding.requests.get')
    def test_get_coordinates_invalid_json(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        lat, lon = get_coordinates("São Paulo")
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    @patch('app.geocoding.requests.get')
    def test_get_coordinates_invalid_coordinates(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "results": [
                {
                    "latitude": 91,  # Invalid
                    "longitude": -46.6333
                }
            ]
        }
        mock_get.return_value = mock_response

        lat, lon = get_coordinates("São Paulo")
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    @patch('app.geocoding.requests.get')
    def test_get_coordinates_missing_keys(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "results": [
                {
                    "lat": -23.5505,  # Wrong key
                    "lon": -46.6333
                }
            ]
        }
        mock_get.return_value = mock_response

        lat, lon = get_coordinates("São Paulo")
        self.assertIsNone(lat)
        self.assertIsNone(lon)


if __name__ == '__main__':
    unittest.main()