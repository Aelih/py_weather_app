from fastapi import FastAPI, Depends, Form, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from database import engine, get_db
from weather_client import WeatherClient

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Weather App")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    # Извлекаем последние 10 запросов для истории
    history = db.query(models.WeatherRequest).order_by(models.WeatherRequest.id.desc()).limit(10).all()
    
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"history": history, "weather": None, "error": None}
    )


@app.post("/weather/search", response_class=HTMLResponse)
async def search(request: Request, city: str = Form(...), db: Session = Depends(get_db)):
    client = WeatherClient(db)
    error = None
    weather = None
    
    city_stripped = city.strip()
    
    if not city_stripped:
        error = "Введите название города"
    else:
        try:
            # Запрашиваем погоду у клиента (он теперь ВСЕГДА пишет логи при каждом запросе)
            weather = await client.fetch(city_stripped)
        except ValueError:
            error = f"Город '{city_stripped}' не найден"
        except Exception:
            error = "Ошибка внешнего API погоды"

    # Загружаем обновленную историю (она сразу покажет дубликаты, если кликали один город)
    history = db.query(models.WeatherRequest).order_by(models.WeatherRequest.id.desc()).limit(10).all()
    
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"history": history, "weather": weather, "error": error}
    )