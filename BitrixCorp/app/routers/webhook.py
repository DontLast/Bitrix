import os
import random
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from faker import Faker

from ..database import get_db
from ..models import Company, Contact
from ..bitrix_client import BitrixClient

router = APIRouter(prefix="/bitrix", tags=["bitrix"])


@router.post("/webhook")
async def trigger_seed(
	secret: str | None = Query(default=None),
	db: Session = Depends(get_db),
):
	configured_secret = os.getenv("BITRIX_WEBHOOK_SECRET")
	if configured_secret:
		if not secret or secret != configured_secret:
			raise HTTPException(status_code=403, detail="Forbidden: invalid secret")

	fake = Faker("ru_RU")

	# Создаём 100 компаний
	companies: list[Company] = []
	for _ in range(100):
		company = Company(name=fake.company())
		db.add(company)
		companies.append(company)

	db.flush()

	# Перемешиваем компании и создаём по одному контакту на каждую
	random.shuffle(companies)
	for company in companies:
		gender_val = random.choice(["male", "female"])  # для телефона/имени не критично
		if gender_val == "male":
			first_name = Faker("ru_RU").first_name_male()
			last_name = Faker("ru_RU").last_name_male()
		else:
			first_name = Faker("ru_RU").first_name_female()
			last_name = Faker("ru_RU").last_name_female()

		age = random.randint(18, 75)
		phone = Faker("ru_RU").phone_number()

		contact = Contact(
			first_name=first_name,
			last_name=last_name,
			gender=gender_val,
			age=age,
			phone=phone,
			company_id=company.id,
		)
		db.add(contact)

	db.commit()
	return {"status": "ok", "companies": 100, "contacts": 100}


@router.post("/webhook/push-to-bitrix")
async def push_to_bitrix(
	secret: str | None = Query(default=None),
	count: int = Query(default=100, ge=1, le=500),
):
	configured_secret = os.getenv("BITRIX_WEBHOOK_SECRET")
	if configured_secret:
		if not secret or secret != configured_secret:
			raise HTTPException(status_code=403, detail="Forbidden: invalid secret")

	# Проверка наличия URL вебхука Bitrix
	try:
		client = BitrixClient()
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

	fake = Faker("ru_RU")

	# Создаём компании и контакты непосредственно в Bitrix24
	created_companies: list[int] = []
	created_contacts: list[int] = []

	for _ in range(count):
		company_title = fake.company()
		company_id = await client.create_company(company_title)
		created_companies.append(company_id)

	# Перемешиваем порядок компаний и создаём по одному контакту на каждую
	random.shuffle(created_companies)
	for company_id in created_companies:
		gender_val = random.choice(["male", "female"])  # используем для имени
		if gender_val == "male":
			first_name = Faker("ru_RU").first_name_male()
			last_name = Faker("ru_RU").last_name_male()
		else:
			first_name = Faker("ru_RU").first_name_female()
			last_name = Faker("ru_RU").last_name_female()
		phone = Faker("ru_RU").phone_number()
		contact_id = await client.create_contact(
			first_name=first_name,
			last_name=last_name,
			phone=phone,
			gender=gender_val,
			company_id=company_id,
		)
		created_contacts.append(contact_id)

	return {
		"status": "ok",
		"bitrix_companies": len(created_companies),
		"bitrix_contacts": len(created_contacts),
	}


@router.post("/clear")
async def clear_all(
	secret: str | None = Query(default=None),
	db: Session = Depends(get_db),
):
	configured_secret = os.getenv("BITRIX_WEBHOOK_SECRET")
	if configured_secret:
		if not secret or secret != configured_secret:
			raise HTTPException(status_code=403, detail="Forbidden: invalid secret")

	# Удаляем все контакты, затем компании
	db.query(Contact).delete()
	db.query(Company).delete()
	db.commit()
	return {"status": "ok", "deleted": "all"}
