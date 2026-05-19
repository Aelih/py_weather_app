from fastapi import FastAPI, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from database import engine, get_db
from weather_client import WeatherClient

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Weather App")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    # Извлекаем последние 10 запросов для истории
    history = db.query(models.WeatherRequest).order_by(models.WeatherRequest.id.desc()).limit(10).all()
    
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"history": history, "weather": None, "error": None}
    )


@app.post("/")
async def get_weather(city: str = Form(...), db: Session = Depends(get_db)):
    # 1. Мы БОЛЬШЕ НЕ ИЩЕМ город в базе перед запросом.
    # 2. Всегда идем в Open-Meteo за свежими данными:
    weather_data = await weather_client.get_weather(city)
    
    if not weather_data:
        # Тут ваша обработка ошибки, если город не найден
        return templates.TemplateResponse("index.html", {"request": request, "error": "Город не найден"})
    
    # 3. ВСЕГДА создаем новую запись для истории (каждый клик = новая строка)
    new_log = WeatherRequest(
        city=weather_data["city"],
        country=weather_data["country"],
        temperature=weather_data["temperature"],
        condition=weather_data["condition"],
        wind_speed=weather_data["wind_speed"]
        # fetched_at подставится автоматически благодаря вашей lambda в models.py!
    )
    
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
    # 4. Для отображения истории на странице берем, например, 10 последних записей
    history = db.query(WeatherRequest).order_by(WeatherRequest.fetched_at.desc()).limit(10).all()
    
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "current_weather": new_log, "history": history}
    )