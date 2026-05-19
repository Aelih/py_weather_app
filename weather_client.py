from datetime import datetime, timedelta
import zoneinfo
import httpx
from sqlalchemy.orm import Session
from models import WeatherRequest

WEATHER_CODES = {
    0: "Ясно", 1: "Преимущественно ясно", 2: "Переменная облачность", 3: "Пасмурно",
    45: "Туман", 48: "Изморозь", 51: "Легкая морось", 61: "Слабый дождь",
    63: "Умеренный дождь", 65: "Сильный дождь", 71: "Слабый снегопад",
    73: "Снегопад", 95: "Гроза"
}

class WeatherClient:
    def __init__(self, db: Session):
        self.db = db
        self.tz = zoneinfo.ZoneInfo("Asia/Almaty")

    async def fetch(self, city: str) -> dict:
        time_threshold = datetime.now(self.tz) - timedelta(minutes=30)
        
        # Поиск в кэше (Реализация симуляции .downcase из Rails через LIKE)
        cached_request = self.db.query(WeatherRequest).filter(
            WeatherRequest.city.like(city),
            WeatherRequest.fetched_at > time_threshold.replace(tzinfo=None)
        ).order_by(WeatherRequest.id.desc()).first()

        if cached_request:
            return self._serialize(cached_request)

        return await self._fetch_from_api(city)

    async def _fetch_from_api(self, city: str) -> dict:
        async with httpx.AsyncClient() as client:
            # 1. Поиск координат города (Геокодинг)
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=ru"
            geo_res = await client.get(geo_url)
            geo_data = geo_res.json()

            if not geo_data.get("results"):
                raise ValueError("City not found")

            location = geo_data["results"][0]
            lat, lon = location["latitude"], location["longitude"]
            city_name = location["name"]
            country_name = location.get("country", "Неизвестно")

            # 2. Запрос погоды
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            weather_res = await client.get(weather_url)
            weather_data = weather_res.json().get("current_weather", {})

            if not weather_data:
                raise Exception("API Error")

            code = weather_data.get("weathercode", 0)
            condition_str = WEATHER_CODES.get(code, "Переменная облачность")

            # 3. Запись в историю/кэш
            new_request = WeatherRequest(
                city=city_name,
                country=country_name,
                temperature=weather_data.get("temperature"),
                condition=condition_str,
                wind_speed=weather_data.get("windspeed")
            )
            self.db.add(new_request)
            self.db.commit()
            self.db.refresh(new_request)

            return self._serialize(new_request)

    def _serialize(self, request: WeatherRequest) -> dict:
        return {
            "city": request.city,
            "country": request.country,
            "temperature": request.temperature,
            "condition": request.condition,
            "wind_speed": request.wind_speed,
            "fetched_at": request.fetched_at.strftime("%Y-%m-%d %H:%M:%S")
        }