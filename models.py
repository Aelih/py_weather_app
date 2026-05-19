from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import Column, Integer, String, Float, DateTime
from database import Base

class WeatherRequest(Base):
    __tablename__ = "weather_requests"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True)
    country = Column(String)
    temperature = Column(Float)
    condition = Column(String)
    wind_speed = Column(Float)
    
    # Сохраняем "наивное" время (без сдвига), соответствующее таймзоне Asia/Novosibirsk
    fetched_at = Column(
        DateTime, 
        default=lambda: datetime.now(ZoneInfo("Asia/Novosibirsk")).replace(tzinfo=None)
    )