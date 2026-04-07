import requests
import logging
import datetime
from typing import Optional, Dict, Any, List
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CACHE_EXPIRATION_SECONDS = 600
MAX_CACHE_SIZE = 1000
cache = {}

# Reutilizar sessão (melhor performance e segurança)
session = requests.Session()
session.verify = True

# Configurações de rate limiting
RATE_LIMIT_DELAY = 1.0
last_request_time = 0


def _is_valid_coords(lat: float, lon: float) -> bool:
    """Valida coordenadas geográficas."""
    return isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and \
           -90 <= lat <= 90 and -180 <= lon <= 180


def _apply_rate_limit() -> None:
    """Aplica limite de taxa para evitar bloqueio pela API."""
    global last_request_time
    elapsed = time.time() - last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    last_request_time = time.time()


def _validate_response_data(data: Dict[str, Any], required_keys: List[str]) -> bool:
    """Valida se a resposta JSON contém as chaves necessárias."""
    return all(key in data for key in required_keys)


def _format_date_br(date_str: str) -> str:
    """Mantido (caso queira usar em outro lugar)."""
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%d/%m/%Y")
    except ValueError as e:
        logging.error(f"Erro ao formatar data '{date_str}': {e}")
        return date_str


# 🔥 NOVO — DIA DA SEMANA (PROFISSIONAL)
def _format_day_name(date_str: str) -> str:
    """
    Converte data ISO para dia da semana em português.
    Ex: 2026-04-07 -> Ter
    """
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        return dias[date_obj.weekday()]
    except ValueError as e:
        logging.error(f"Erro ao converter dia da semana: {e}")
        return date_str


def get_weather_data(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    if not _is_valid_coords(lat, lon):
        logging.warning("Coordenadas inválidas fornecidas")
        return None

    _apply_rate_limit()

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,windspeed_10m,relative_humidity_2m,precipitation"
    }

    try:
        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logging.error(f"Falha na requisição para coordenadas ({lat}, {lon}): {e}")
        return None

    if not _validate_response_data(data, ["current"]):
        logging.error("Resposta da API incompleta ou inválida")
        return None

    try:
        current = data["current"]
        return {
            "temperature": int(round(current["temperature_2m"])),
            "windspeed": float(current["windspeed_10m"]),
            "humidity": int(round(current["relative_humidity_2m"])),
            "precipitation": float(current["precipitation"])
        }
    except (KeyError, TypeError, ValueError) as e:
        logging.error(f"Erro ao processar dados atuais: {e}")
        return None

def get_5_day_forecast(lat: float, lon: float) -> Optional[List[Dict[str, Any]]]:
    """
    Obtém previsão dos próximos 5 dias (EXCLUINDO HOJE)
    e formatando como Seg, Ter, Qua...
    """
    if not _is_valid_coords(lat, lon):
        logging.warning("Coordenadas inválidas para forecast")
        return None

    _apply_rate_limit()

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,relative_humidity_2m_mean",
        "timezone": "auto",
        "forecast_days": 6  # 🔥 pede 6 dias
    }

    try:
        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logging.error(f"Erro na requisição de forecast para ({lat}, {lon}): {e}")
        return None

    if not _validate_response_data(data, ["daily"]):
        logging.error("Resposta de forecast incompleta")
        return None

    try:
        daily = data["daily"]
        forecast = []

        # 🔥 IGNORA O DIA ATUAL
        for date, tmax, tmin, rain, wind, hum in list(zip(
            daily["time"],
            daily["temperature_2m_max"],
            daily["temperature_2m_min"],
            daily["precipitation_sum"],
            daily["windspeed_10m_max"],
            daily["relative_humidity_2m_mean"]
        ))[1:6]:

            forecast.append({
                "date": f"{_format_day_name(date)} • {datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m')}",
                "temp_max": int(round(tmax)),
                "temp_min": int(round(tmin)),
                "precipitation_sum": float(rain),
                "windspeed_max": float(wind),
                "humidity_avg": int(round(hum))
            })

        return forecast

    except (KeyError, TypeError, ValueError) as e:
        logging.error(f"Erro ao processar forecast: {e}")
        return None


def get_cached_weather_data(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    key = (round(lat, 4), round(lon, 4))
    now = datetime.datetime.now()

    if key in cache:
        cached = cache[key]
        if (now - cached["timestamp"]).total_seconds() < CACHE_EXPIRATION_SECONDS:
            return cached["data"]

    data = get_weather_data(lat, lon)

    if data:
        if len(cache) >= MAX_CACHE_SIZE:
            oldest_key = min(cache, key=lambda k: cache[k]["timestamp"])
            del cache[oldest_key]

        cache[key] = {"data": data, "timestamp": now}

    return data