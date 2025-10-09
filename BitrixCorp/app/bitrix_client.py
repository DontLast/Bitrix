import os
import time
import asyncio
from typing import Any, Dict, List
import httpx
from dotenv import load_dotenv

load_dotenv()

# Жёстко заданный URL вебхука Bitrix24 (используется всегда)
BITRIX_WEBHOOK_URL = "https://b24-25ltxt.bitrix24.ru/rest/1/xdimdye9gomtwy6n/".rstrip("/")


class BitrixClient:
	def __init__(self, base_url: str | None = None):
		base = (base_url or BITRIX_WEBHOOK_URL).rstrip("/")
		# Если по ошибке передали полный метод (напр. .../profile.json), отрежем последний сегмент
		if base.endswith(".json"):
			base = base.rsplit("/", 1)[0]
		self.base_url = base
		if not self.base_url:
			raise ValueError("BITRIX_WEBHOOK_URL is not configured")

	async def _call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
		url = f"{self.base_url}/{method}"
		attempts = 0
		last_exc: Exception | None = None
		while attempts < 5:
			attempts += 1
			try:
				async with httpx.AsyncClient(timeout=30) as client:
					resp = await client.post(url, json=params)
					status = resp.status_code
					if status in (429, 500, 502, 503, 504):
						raise httpx.HTTPStatusError("transient", request=resp.request, response=resp)
					resp.raise_for_status()
					data = resp.json()
					if "error" in data:
						raise RuntimeError(f"Bitrix error: {data.get('error_description') or data['error']}")
					return data
			except httpx.HTTPStatusError as e:
				last_exc = e
				# Пытаемся отдать тело ответа Bitrix для диагностики
				try:
					payload = e.response.json()
					msg = payload.get("error_description") or payload.get("error") or e.response.text
				except Exception:
					msg = e.response.text if e.response is not None else str(e)
				# экспоненциальный бэкоф (неблокирующий)
				delay = min(2 ** attempts, 10)
				await asyncio.sleep(delay)
			except Exception as e:
				last_exc = e
				break
		# если не удалось
		raise RuntimeError(f"HTTP error calling {method}: {last_exc}")

	async def create_company(self, title: str) -> int:
		payload = {
			"fields": {
				"TITLE": title,
			},
			"params": {"REGISTER_SONET_EVENT": "Y"},
		}
		data = await self._call("crm.company.add.json", payload)
		return int(data.get("result"))

	async def delete_company(self, company_id: int) -> bool:
		data = await self._call("crm.company.delete.json", {"id": int(company_id)})
		return bool(data.get("result"))

	async def list_company_ids(self, limit: int = 1000) -> List[int]:
		items = await self.list_companies(limit=limit)
		return [int(i["ID"]) for i in items]

	async def create_contact(self, first_name: str, last_name: str, phone: str, gender: str | None = None, company_id: int | None = None, middle_name: str | None = None) -> int:
		fields: Dict[str, Any] = {
			"NAME": first_name,
			"LAST_NAME": last_name,
			"PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}],
		}
		if middle_name:
			fields["SECOND_NAME"] = middle_name
		if company_id is not None:
			fields["COMPANY_ID"] = company_id
		payload = {
			"fields": fields,
			"params": {"REGISTER_SONET_EVENT": "Y"},
		}
		data = await self._call("crm.contact.add.json", payload)
		return int(data.get("result"))

	async def delete_contact(self, contact_id: int) -> bool:
		data = await self._call("crm.contact.delete.json", {"id": int(contact_id)})
		return bool(data.get("result"))

	async def list_contact_ids(self, limit: int = 2000) -> List[int]:
		items = await self.list_contacts(limit=limit)
		return [int(i["ID"]) for i in items]

	async def list_companies(self, limit: int = 100) -> List[Dict[str, Any]]:
		payload = {
			"order": {"ID": "DESC"},
			"filter": {},
			"select": ["ID", "TITLE"],
			"start": 0,
		}
		results: List[Dict[str, Any]] = []
		while True:
			data = await self._call("crm.company.list.json", payload)
			items = data.get("result", [])
			results.extend(items)
			if len(results) >= limit or not data.get("next"):
				break
			payload["start"] = data["next"]
		return results[:limit]

	async def list_contacts(self, limit: int = 100) -> List[Dict[str, Any]]:
		payload = {
			"order": {"ID": "DESC"},
			"filter": {},
			"select": ["ID", "NAME", "SECOND_NAME", "LAST_NAME", "PHONE", "COMPANY_ID"],
			"start": 0,
		}
		results: List[Dict[str, Any]] = []
		while True:
			data = await self._call("crm.contact.list.json", payload)
			items = data.get("result", [])
			results.extend(items)
			if len(results) >= limit or not data.get("next"):
				break
			payload["start"] = data["next"]
		return results[:limit]
