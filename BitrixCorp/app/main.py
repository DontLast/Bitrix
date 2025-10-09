from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

from .routers.webhook import router as bitrix_router
from .bitrix_client import BitrixClient

app = FastAPI(title="BitrixCorp")

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
	secret = os.getenv("BITRIX_WEBHOOK_SECRET") or ""
	companies_view = []
	contacts_view = []
	error_message = ""
	try:
		client = BitrixClient()
		companies = await client.list_companies(limit=100)
		contacts = await client.list_contacts(limit=1000)

		# Построим отображение ID компании -> название
		company_id_to_title = {int(c["ID"]): c.get("TITLE", "") for c in companies}

		# Подготовим представление компаний с составом
		for c in companies:
			cid = int(c["ID"])
			members = [
				f"{p.get('LAST_NAME','')} {p.get('NAME','')} {p.get('SECOND_NAME','')}".strip()
				for p in contacts
				if (str(p.get("COMPANY_ID")) == str(cid))
			]
			companies_view.append({
				"id": cid,
				"title": c.get("TITLE", ""),
				"members": members,
			})

		# Подготовим представление контактов с названием компании
		for p in contacts:
			cid = p.get("COMPANY_ID")
			contacts_view.append({
				"id": int(p["ID"]),
				"last_name": p.get("LAST_NAME", ""),
				"first_name": p.get("NAME", ""),
				"middle_name": p.get("SECOND_NAME", ""),
				"gender": "",
				"age": "",
				"phone": p.get("PHONE", [{}])[0].get("VALUE", "") if isinstance(p.get("PHONE"), list) and p.get("PHONE") else "",
				"company_title": company_id_to_title.get(int(cid)) if cid else "",
			})
	except Exception as e:
		error_message = str(e)

	return templates.TemplateResponse(
		"index.html",
		{"request": request, "companies": companies_view, "contacts": contacts_view, "webhook_secret": secret, "error_message": error_message},
	)


# Роуты Bitrix
app.include_router(bitrix_router)
