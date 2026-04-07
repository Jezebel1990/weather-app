import unittest
from unittest.mock import patch, MagicMock, mock_open
import io
import sys
from app.main import main


class TestMainFunction(unittest.TestCase):

    @patch('app.main.get_coordinates')
    @patch('app.main.get_cached_weather_data')
    @patch('app.main.get_5_day_forecast')
    @patch('builtins.input')
    @patch('builtins.open', new_callable=mock_open)
    def test_main_success_single_city(self, mock_file, mock_input, mock_forecast, mock_weather, mock_coords):
        # Setup mocks
        mock_input.return_value = "São Paulo"
        mock_coords.return_value = (-23.5505, -46.6333)
        mock_weather.return_value = {
            "temperature": 25,
            "windspeed": 10.5,
            "humidity": 60,
            "precipitation": 0.0
        }
        mock_forecast.return_value = [
            {
                "date": "Ter • 08/04",
                "temp_max": 28,
                "temp_min": 18,
                "precipitation_sum": 0.0,
                "windspeed_max": 15.0,
                "humidity_avg": 65
            }
        ]

        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            main()
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()

        # Assertions
        self.assertIn("=== São Paulo ===", output)
        self.assertIn("Temperatura: 25°C", output)
        self.assertIn("Vento: 10.5 km/h", output)
        self.assertIn("Umidade: 60%", output)
        self.assertIn("Precipitação: 0.0 mm", output)
        self.assertIn("Previsão de 5 dias:", output)
        self.assertIn("Ter • 08/04", output)

        # Check file write
        mock_file.assert_called_once_with("weather_log.txt", "a", encoding="utf-8")
        handle = mock_file()
        handle.write.assert_called_once()

    @patch('app.main.get_coordinates')
    @patch('builtins.input')
    def test_main_empty_input(self, mock_input, mock_coords):
        mock_input.return_value = ""

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            main()
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertIn("Nomes das cidades não podem ficar vazios.", output)
        mock_coords.assert_not_called()

    @patch('app.main.get_coordinates')
    @patch('builtins.input')
    def test_main_invalid_cities(self, mock_input, mock_coords):
        mock_input.return_value = "Cidade1,   , Cidade2"
        mock_coords.side_effect = [(None, None), (None, None)]

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            main()
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertIn("Cidade 'Cidade1' não encontrada.", output)
        self.assertIn("Cidade 'Cidade2' não encontrada.", output)
        self.assertIn("Nenhuma cidade válida.", output)

    @patch('app.main.get_coordinates')
    @patch('app.main.get_cached_weather_data')
    @patch('builtins.input')
    def test_main_weather_error(self, mock_input, mock_weather, mock_coords):
        mock_input.return_value = "São Paulo"
        mock_coords.return_value = (-23.5505, -46.6333)
        mock_weather.return_value = None

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            main()
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertIn("Erro ao obter clima para São Paulo", output)

    @patch('app.main.get_coordinates')
    @patch('app.main.get_cached_weather_data')
    @patch('app.main.get_5_day_forecast')
    @patch('builtins.input')
    @patch('builtins.open', new_callable=mock_open)
    def test_main_multiple_cities(self, mock_file, mock_input, mock_forecast, mock_weather, mock_coords):
        mock_input.return_value = "São Paulo, Rio de Janeiro"
        mock_coords.side_effect = [(-23.5505, -46.6333), (-22.9068, -43.1729)]
        mock_weather.side_effect = [
            {"temperature": 25, "windspeed": 10.5, "humidity": 60, "precipitation": 0.0},
            {"temperature": 28, "windspeed": 12.0, "humidity": 70, "precipitation": 1.0}
        ]
        mock_forecast.return_value = None  # No forecast for simplicity

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            main()
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()

        self.assertIn("=== São Paulo ===", output)
        self.assertIn("=== Rio de Janeiro ===", output)
        self.assertIn("Temperatura: 25°C", output)
        self.assertIn("Temperatura: 28°C", output)

    @patch('app.main.get_coordinates')
    @patch('app.main.get_cached_weather_data')
    @patch('app.main.get_5_day_forecast')
    @patch('builtins.input')
    @patch('builtins.open', new_callable=mock_open)
    def test_main_forecast_error(self, mock_file, mock_input, mock_forecast, mock_weather, mock_coords):
        mock_input.return_value = "São Paulo"
        mock_coords.return_value = (-23.5505, -46.6333)
        mock_weather.return_value = {
            "temperature": 25,
            "windspeed": 10.5,
            "humidity": 60,
            "precipitation": 0.0
        }
        mock_forecast.return_value = None

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            main()
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertIn("Erro ao obter previsão.", output)


if __name__ == '__main__':
    unittest.main()