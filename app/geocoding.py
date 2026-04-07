import logging
import requests
from typing import Tuple, Optional
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurações de segurança
MAX_CITY_NAME_LENGTH = 100
RATE_LIMIT_DELAY = 0.5  # segundos entre requisições
last_request_time = 0


def _is_valid_city_name(city: str) -> bool:
    """
    Valida o nome da cidade para evitar injeção e dados inválidos.
    
    Args:
        city (str): Nome da cidade a validar.
    
    Returns:
        bool: True se o nome é válido, False caso contrário.
    """
    if not city or not isinstance(city, str):
        return False
    
    # Remove espaços e verifica comprimento
    city = city.strip()
    if len(city) == 0 or len(city) > MAX_CITY_NAME_LENGTH:
        return False
    
    # Permite apenas caracteres alfanuméricos, espaços e hífens
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -áàâãäéèêëíìîïóòôõöúùûüçñ')
    return all(char in allowed_chars for char in city)


def _is_valid_coordinates(lat: float, lon: float) -> bool:
    """
    Valida se as coordenadas estão dentro dos limites geográficos.
    
    Args:
        lat (float): Latitude.
        lon (float): Longitude.
    
    Returns:
        bool: True se as coordenadas são válidas.
    """
    return isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and \
           -90 <= lat <= 90 and -180 <= lon <= 180


def _apply_rate_limit() -> None:
    """
    Aplica limite de taxa para evitar bloqueio pela API.
    """
    global last_request_time
    elapsed = time.time() - last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    last_request_time = time.time()


def get_coordinates(city: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Obtém coordenadas geográficas (latitude e longitude) para uma cidade.
    
    Esta função consulta a API Open-Meteo Geocoding para converter um nome de cidade
    em coordenadas geográficas precisas. Os dados retornados podem ser usados em
    outras funções para obter dados meteorológicos.
    
    Args:
        city (str): Nome da cidade (máximo 100 caracteres).
                   Exemplos válidos: "São Paulo", "New York", "London", "Paris-France"
    
    Returns:
        Tuple[Optional[float], Optional[float]]: Uma tupla contendo (latitude, longitude).
        - Retorna (None, None) se o nome da cidade for inválido, não encontrado ou
          houver erro na requisição.
        - Caso contrário, retorna (float, float) com as coordenadas válidas.
    
    Raises:
        Nenhum erro é levantado diretamente; erros são logados.
    
    Example:
        >>> lat, lon = get_coordinates("São Paulo")
        >>> if lat and lon:
        ...     print(f"Coordenadas: {lat}, {lon}")
        ...     # Usar em: get_weather_data(lat, lon)
        Coordenadas: -23.5505, -46.6333
        
        >>> lat, lon = get_coordinates("Cidade Inválida!!!!")
        >>> print(lat, lon)
        None None
    """
    # Validação de entrada
    if not _is_valid_city_name(city):
        logging.warning(f"Nome de cidade inválido ou suspeito: {city}")
        return None, None
    
    city = city.strip()
    
    # Aplicar rate limiting
    _apply_rate_limit()
    
    url = "https://geocoding-api.open-meteo.com/v1/search"
    
    params = {
        "name": city,
        "count": 1,
        "language": "pt"  # Idioma português para melhor compatibilidade
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
    except requests.exceptions.Timeout:
        logging.error(f"Timeout ao buscar coordenadas para: {city}")
        return None, None
    except requests.exceptions.HTTPError as e:
        logging.error(f"Erro HTTP ao buscar coordenadas para {city}: {e.response.status_code}")
        return None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na requisição para cidade '{city}': {e}")
        return None, None
    except ValueError as e:
        logging.error(f"Erro ao decodificar JSON da resposta: {e}")
        return None, None
    
    # Validação de resposta
    if not data.get("results") or len(data["results"]) == 0:
        logging.info(f"Cidade não encontrada: {city}")
        return None, None
    
    try:
        result = data["results"][0]
        latitude = float(result.get("latitude"))
        longitude = float(result.get("longitude"))
        
        # Validação adicional das coordenadas
        if not _is_valid_coordinates(latitude, longitude):
            logging.error(f"Coordenadas inválidas retornadas para '{city}': {latitude}, {longitude}")
            return None, None
        
        logging.info(f"Coordenadas obtidas para '{city}': {latitude}, {longitude}")
        return latitude, longitude
        
    except (KeyError, ValueError, TypeError) as e:
        logging.error(f"Erro ao processar dados da API para '{city}': {e}")
        return None, None