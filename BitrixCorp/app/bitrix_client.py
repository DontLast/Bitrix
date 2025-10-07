import os
from typing import Any, Dict
import httpx
from dotenv import load_dotenv

load_dotenv()

BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "").rstrip("/")


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
		async with httpx.AsyncClient(timeout=30) as client:
			resp = await client.post(url, json=params)
			resp.raise_for_status()
			data = resp.json()
			if "error" in data:
				raise RuntimeError(f"Bitrix error: {data.get('error_description') or data['error']}")
			return data

	async def create_company(self, title: str) -> int:
		payload = {
			"fields": {
				"TITLE": title,
			},
			"params": {"REGISTER_SONET_EVENT": "Y"},
		}
		data = await self._call("crm.company.add.json", payload)
		return int(data.get("result"))

	async def create_contact(self, first_name: str, last_name: str, phone: str, gender: str | None = None, company_id: int | None = None) -> int:
		fields: Dict[str, Any] = {
			"NAME": first_name,
			"LAST_NAME": last_name,
			"PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}],
		}
		# Пол не является стандартным полем, пропускаем или используем кастомные поля при наличии
		if company_id is not None:
			fields["COMPANY_ID"] = company_id
		payload = {
			"fields": fields,
			"params": {"REGISTER_SONET_EVENT": "Y"},
		}
		data = await self._call("crm.contact.add.json", payload)
		return int(data.get("result"))
