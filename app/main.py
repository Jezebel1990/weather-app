from app.geocoding import get_coordinates
from app.weather import get_cached_weather_data, get_5_day_forecast
import datetime
import concurrent.futures

def main():
    cities_input = input("Digite os nomes das cidades separados por vírgula: ").strip()
    if not cities_input:
        print("Nomes das cidades não podem ficar vazios.")
        return

    cities = [city.strip() for city in cities_input.split(',') if city.strip()]
    if not cities:
        print("Nenhuma cidade válida fornecida.")
        return

    # Obter coordenadas
    city_coords = []
    for city in cities:
        lat, lon = get_coordinates(city)
        if lat is None or lon is None:
            print(f"Cidade '{city}' não encontrada.")
            continue
        city_coords.append((city, lat, lon))

    if not city_coords:
        print("Nenhuma cidade válida.")
        return

    # Buscar clima atual em paralelo
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_city = {
            executor.submit(get_cached_weather_data, lat, lon): (city, lat, lon)
            for city, lat, lon in city_coords
        }

        results = []
        for future in concurrent.futures.as_completed(future_to_city):
            city, lat, lon = future_to_city[future]
            try:
                weather_data = future.result()
                if weather_data:
                    results.append((city, lat, lon, weather_data))
                else:
                    print(f"Erro ao obter clima para {city}")
            except Exception as e:
                print(f"Erro em {city}: {e}")

    # Exibir resultados
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open("weather_log.txt", "a", encoding="utf-8") as f:
        for city, lat, lon, weather_data in results:
            print(f"\n=== {city} ===")
            print(f"Temperatura: {weather_data['temperature']}°C")
            print(f"Vento: {weather_data['windspeed']} km/h")
            print(f"Umidade: {weather_data['humidity']}%")
            print(f"Precipitação: {weather_data['precipitation']} mm (última hora)") # Exibindo a precipitação

            f.write(f"{timestamp}: {city} - {weather_data}\n")

            # Forecast
            forecast = get_5_day_forecast(lat, lon)
            if forecast:
                print("\nPrevisão de 5 dias:")
                for day in forecast:
                    print(
                        f"{day['date']} | "
                        f"Min: {day['temp_min']}°C / Max: {day['temp_max']}°C | "
                        f"Chuva: {day['precipitation_sum']} mm | "
                        f"Vento: {day['windspeed_max']} km/h | "
                        f"Umidade: {day['humidity_avg']}%"
                    )
            else:
                print("Erro ao obter previsão.")

if __name__ == "__main__":
    main()