"""
OpenWeatherMap ile hava durumu servisi.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# OpenWeatherMap weather.main değerleri → Türkçe kısa açıklama
WEATHER_MAIN_TR = {
    "Clear": "Güneşli",
    "Clouds": "Bulutlu",
    "Rain": "Yağmurlu",
    "Drizzle": "Çisentili",
    "Thunderstorm": "Gök gürültülü sağanak",
    "Snow": "Karlı",
    "Mist": "Sisli",
    "Fog": "Sisli",
    "Haze": "Puslu",
    "Dust": "Tozlu",
    "Sand": "Kum fırtınası",
    "Ash": "Kül",
    "Squall": "Sert rüzgarlı",
    "Tornado": "Fırtınalı",
}


def get_weather_data(city):
    """
    OpenWeatherMap API ile şehir bazlı hava durumu verisi al.

    Args:
        city: Şehir adı (örn: "Istanbul", "İzmir"). Boşsa None döner.

    Returns:
        dict veya None:
            - temp: Sıcaklık (°C)
            - feels_like: Hissedilen sıcaklık (°C)
            - condition: Gökyüzü durumu (Güneşli, Yağmurlu vb.)
            - condition_key: Orijinal anahtar (Rain, Clear vb.)
            - is_rainy: Yağış var mı (yağmur/çisentili/fırtına)
            - city_name: API'den dönen şehir adı
    """
    if not city or not city.strip():
        return None

    api_key = getattr(settings, "OPENWEATHER_API_KEY", "") or ""
    if not api_key:
        logger.debug("OPENWEATHER_API_KEY tanımlı değil, hava durumu atlanıyor")
        return None

    city_clean = city.strip()
    # Türkiye şehirleri için country code ekle (API daha iyi eşleşir)
    if "turkey" not in city_clean.lower() and "türkiye" not in city_clean.lower():
        query = f"{city_clean},TR"
    else:
        query = city_clean

    # 1. Geocoding: şehir adı → enlem, boylam
    geo_url = "https://api.openweathermap.org/geo/1.0/direct"
    geo_params = {"q": query, "limit": 1, "appid": api_key}

    try:
        geo_resp = requests.get(geo_url, params=geo_params, timeout=8)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
    except requests.RequestException as e:
        logger.warning("OpenWeatherMap Geocoding hatası: %s", e)
        return None
    except ValueError:
        return None

    if not geo_data or not isinstance(geo_data, list) or len(geo_data) == 0:
        return None

    lat = geo_data[0].get("lat")
    lon = geo_data[0].get("lon")
    city_name = geo_data[0].get("name", city_clean)

    if lat is None or lon is None:
        return None

    # 2. Current weather
    weather_url = "https://api.openweathermap.org/data/2.5/weather"
    weather_params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
        "lang": "tr",
    }

    try:
        weather_resp = requests.get(weather_url, params=weather_params, timeout=8)
        weather_resp.raise_for_status()
        data = weather_resp.json()
    except requests.RequestException as e:
        logger.warning("OpenWeatherMap Weather hatası: %s", e)
        return None
    except ValueError:
        return None

    main = data.get("main", {})
    weather_list = data.get("weather", [])
    condition_key = weather_list[0].get("main", "Unknown") if weather_list else "Unknown"
    condition = WEATHER_MAIN_TR.get(condition_key, condition_key)
    temp = main.get("temp")
    feels_like = main.get("feels_like", temp)

    is_rainy = condition_key in ("Rain", "Drizzle", "Thunderstorm")

    return {
        "temp": round(float(temp), 1) if temp is not None else None,
        "feels_like": round(float(feels_like), 1) if feels_like is not None else None,
        "condition": condition,
        "condition_key": condition_key,
        "is_rainy": is_rainy,
        "city_name": city_name,
    }
