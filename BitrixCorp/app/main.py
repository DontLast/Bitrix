from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os

from .database import Base, engine, get_db
from .models import Company, Contact
from .routers.webhook import router as bitrix_router

app = FastAPI(title="BitrixCorp")

templates = Jinja2Templates(directory="app/templates")

# Создаём таблицы при старте, если их нет
Base.metadata.create_all(bind=engine)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
	companies = db.query(Company).all()
	contacts = db.query(Contact).all()
	secret = os.getenv("BITRIX_WEBHOOK_SECRET") or ""
	return templates.TemplateResponse(
		"index.html",
		{"request": request, "companies": companies, "contacts": contacts, "webhook_secret": secret},
	)


# Роуты Bitrix
app.include_router(bitrix_router)
