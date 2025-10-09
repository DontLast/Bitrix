import os
import random
import asyncio
from fastapi import APIRouter, HTTPException, Query
from faker import Faker
from starlette.responses import StreamingResponse

from ..bitrix_client import BitrixClient

router = APIRouter(prefix="/bitrix", tags=["bitrix"])


@router.get("/webhook/push-stream")
async def push_stream(
	secret: str | None = Query(default=None),
	count: int = Query(default=100, ge=1, le=500),
):
	configured_secret = os.getenv("BITRIX_WEBHOOK_SECRET")
	if configured_secret and (not secret or secret != configured_secret):
		raise HTTPException(status_code=403, detail="Forbidden: invalid secret")

	async def event_gen():
		try:
			client = BitrixClient()
		except Exception as e:
			yield f"data: error: {str(e)}\n\n"
			return

		fake = Faker("ru_RU")
		created_companies: list[int] = []
		done = 0
		total = count * 2  # компании + контакты

		# Создание компаний
		for _ in range(count):
			try:
				company_title = fake.company()
				company_id = await client.create_company(company_title)
				created_companies.append(company_id)
			except Exception as e:
				yield f"data: error: {str(e)}\n\n"
				return
			done += 1
			percent = min((done // 2), 100)
			yield f"data: {percent}\n\n"
			await asyncio.sleep(0.15)

		# Создание контактов
		random.shuffle(created_companies)
		for company_id in created_companies:
			try:
				gender_val = random.choice(["male", "female"])  # используем для имени
				if gender_val == "male":
					first_name = fake.first_name_male()
					last_name = fake.last_name_male()
					middle_name = fake.middle_name_male()
				else:
					first_name = fake.first_name_female()
					last_name = fake.last_name_female()
					middle_name = fake.middle_name_female()
				phone = fake.phone_number()
				await client.create_contact(
					first_name=first_name,
					last_name=last_name,
					phone=phone,
					gender=gender_val,
					company_id=company_id,
					middle_name=middle_name,
				)
			except Exception as e:
				yield f"data: error: {str(e)}\n\n"
				return
			done += 1
			percent = min((done // 2), 100)
			yield f"data: {percent}\n\n"
			await asyncio.sleep(0.15)

		yield "data: done\n\n"

	return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/clear-stream")
async def clear_stream(secret: str | None = Query(default=None)):
	configured_secret = os.getenv("BITRIX_WEBHOOK_SECRET")
	if configured_secret and (not secret or secret != configured_secret):
		raise HTTPException(status_code=403, detail="Forbidden: invalid secret")

	async def event_gen():
		try:
			client = BitrixClient()
		except Exception as e:
			yield f"data: error: {str(e)}\n\n"
			return

		# Получаем полный список
		try:
			contact_ids = await client.list_contact_ids(limit=5000)
			company_ids = await client.list_company_ids(limit=5000)
		except Exception as e:
			yield f"data: error: {str(e)}\n\n"
			return

		done = 0
		total = len(contact_ids) + len(company_ids)
		if total == 0:
			yield "data: 100\n\n"
			yield "data: done\n\n"
			return

		# Удаляем контакты
		for cid in contact_ids:
			try:
				await client.delete_contact(cid)
			except Exception:
				pass
			done += 1
			percent = min((done // 2), 100)
			yield f"data: {percent}\n\n"
			await asyncio.sleep(0.1)

		# Удаляем компании
		for coid in company_ids:
			try:
				await client.delete_company(coid)
			except Exception:
				pass
			done += 1
			percent = min((done // 2), 100)
			yield f"data: {percent}\n\n"
			await asyncio.sleep(0.1)

		yield "data: done\n\n"

	return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post("/webhook/push-to-bitrix")
async def push_to_bitrix(
	secret: str | None = Query(default=None),
	count: int = Query(default=100, ge=1, le=500),
):
	configured_secret = os.getenv("BITRIX_WEBHOOK_SECRET")
	if configured_secret:
		if not secret or secret != configured_secret:
			raise HTTPException(status_code=403, detail="Forbidden: invalid secret")

	# Инициализация клиента Bitrix
	try:
		client = BitrixClient()
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

	fake = Faker("ru_RU")

	created_companies: list[int] = []
	created_contacts: list[int] = []

	try:
		for _ in range(count):
			company_title = fake.company()
			company_id = await client.create_company(company_title)
			created_companies.append(company_id)
			await asyncio.sleep(0.2)

		# Перемешиваем порядок компаний и создаём по одному контакту на каждую
		random.shuffle(created_companies)
		for company_id in created_companies:
			gender_val = random.choice(["male", "female"])  # используем для имени
			if gender_val == "male":
				first_name = Faker("ru_RU").first_name_male()
				last_name = Faker("ru_RU").last_name_male()
				middle_name = Faker("ru_RU").middle_name_male()
			else:
				first_name = Faker("ru_RU").first_name_female()
				last_name = Faker("ru_RU").last_name_female()
				middle_name = Faker("ru_RU").middle_name_female()
			phone = Faker("ru_RU").phone_number()
			contact_id = await client.create_contact(
				first_name=first_name,
				last_name=last_name,
				phone=phone,
				gender=gender_val,
				company_id=company_id,
				middle_name=middle_name,
			)
			created_contacts.append(contact_id)
			await asyncio.sleep(0.2)
	except RuntimeError as e:
		raise HTTPException(status_code=502, detail=f"Bitrix error: {e}")
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

	return {
		"status": "ok",
		"bitrix_companies": len(created_companies),
		"bitrix_contacts": len(created_contacts),
	}


@router.post("/clear-bitrix")
async def clear_bitrix(secret: str | None = Query(default=None)):
	configured_secret = os.getenv("BITRIX_WEBHOOK_SECRET")
	if configured_secret:
		if not secret or secret != configured_secret:
			raise HTTPException(status_code=403, detail="Forbidden: invalid secret")
	try:
		client = BitrixClient()
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))

	# Удаляем сначала контакты, затем компании
	deleted_contacts = 0
	deleted_companies = 0
	try:
		contact_ids = await client.list_contact_ids(limit=5000)
		for cid in contact_ids:
			try:
				if await client.delete_contact(cid):
					deleted_contacts += 1
			except Exception:
				# пропускаем проблемную запись
				pass
			await asyncio.sleep(0.15)

		company_ids = await client.list_company_ids(limit=5000)
		for coid in company_ids:
			try:
				if await client.delete_company(coid):
					deleted_companies += 1
			except Exception:
				pass
			await asyncio.sleep(0.15)
	except RuntimeError as e:
		raise HTTPException(status_code=502, detail=f"Bitrix error: {e}")

	return {"status": "ok", "deleted_contacts": deleted_contacts, "deleted_companies": deleted_companies}
