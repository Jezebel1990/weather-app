from flask import Flask, render_template, request
from geocoding import get_coordinates
from weather import get_cached_weather_data, get_5_day_forecast
import datetime
import os

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)

# 🔥 FUNÇÃO PARA FORMATAR DATA ATUAL
def get_today_label():
    dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    hoje = datetime.datetime.now()
    return f"{dias[hoje.weekday()]}, {hoje.strftime('%d/%m')}"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/weather', methods=['POST'])
def weather():
    city_input = request.form.get('city')

    if not city_input:
        return render_template(
            'index.html',
            error="Digite uma cidade",
            weather_data_list=[]
        )

    # 🔥 separa múltiplas cidades
    cities = [c.strip() for c in city_input.split(",") if c.strip()]

    weather_data_list = []

    for city in cities:
        lat, lon = get_coordinates(city)

        if lat is None or lon is None:
            continue

        current = get_cached_weather_data(lat, lon)
        forecast = get_5_day_forecast(lat, lon) or []

        if not current:
            continue

        weather_data_list.append({
            "city": city.title(),
            "temp": f"{current['temperature']}°C",
            "wind": f"{current['windspeed']} km/h",
            "humidity": f"{current['humidity']}%",
            "rain": f"{current['precipitation']} mm",
            "forecast": forecast,
            "today": get_today_label()  # 🔥 AQUI ESTÁ A CORREÇÃO
        })

    if not weather_data_list:
        return render_template(
            'index.html',
            error="Nenhuma cidade válida encontrada",
            weather_data_list=[]
        )

    return render_template(
        'index.html',
        weather_data_list=weather_data_list
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
