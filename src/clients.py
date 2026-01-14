from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterator
from urllib.parse import urljoin

import requests

from .config import IntegrationConfig


@dataclass(frozen=True)
class Student:
    id: str
    name: str
    phone: str | None


@dataclass(frozen=True)
class Boleto:
    id: str
    due_date: date
    amount: float
    barcode: str
    line_digit: str


class SIGAClient:
    def __init__(self, config: IntegrationConfig, session: requests.Session | None = None) -> None:
        self._config = config
        self._session = session or requests.Session()

    def _headers(self) -> dict[str, str]:
        token = self._config.siga_auth_token
        prefix = self._config.siga_auth_prefix
        return {self._config.siga_auth_header: f"{prefix} {token}".strip()}

    def iter_active_students(self, year: int) -> Iterator[Student]:
        page = 1
        while True:
            params = {
                "ativo": True,
                "ano": year,
                "page": page,
                "pageSize": self._config.siga_page_size,
            }
            url = urljoin(self._config.siga_base_url, self._config.siga_students_endpoint)
            response = self._session.get(url, headers=self._headers(), params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items") or payload.get("data") or []
            for item in items:
                yield Student(
                    id=str(item.get("id") or item.get("codigo") or ""),
                    name=item.get("nome") or item.get("name") or "",
                    phone=item.get("telefone") or item.get("celular") or item.get("phone"),
                )
            total_pages = payload.get("totalPages") or payload.get("pages")
            if total_pages and page >= int(total_pages):
                break
            if not items:
                break
            page += 1

    def get_boletos_due(self, aluno_id: str, start: date, end: date) -> list[Boleto]:
        endpoint = self._config.siga_boletos_endpoint.format(aluno_id=aluno_id)
        params = {
            "dataVencimentoInicio": start.isoformat(),
            "dataVencimentoFim": end.isoformat(),
        }
        url = urljoin(self._config.siga_base_url, endpoint)
        response = self._session.get(url, headers=self._headers(), params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items") or payload.get("data") or []
        boletos: list[Boleto] = []
        for item in items:
            boletos.append(
                Boleto(
                    id=str(item.get("id") or item.get("codigo") or ""),
                    due_date=date.fromisoformat(item.get("dataVencimento")),
                    amount=float(item.get("valor")),
                    barcode=item.get("codigoBarras") or "",
                    line_digit=item.get("linhaDigitavel") or "",
                )
            )
        return boletos


class MegaZapClient:
    def __init__(self, config: IntegrationConfig, session: requests.Session | None = None) -> None:
        self._config = config
        self._session = session or requests.Session()

    def _headers(self) -> dict[str, str]:
        token = self._config.megazap_auth_token
        prefix = self._config.megazap_auth_prefix
        return {
            self._config.megazap_auth_header: f"{prefix} {token}".strip(),
            "Content-Type": "application/json",
        }

    def send_qrcode(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = urljoin(self._config.megazap_base_url, self._config.megazap_qrcode_endpoint)
        response = self._session.post(url, headers=self._headers(), json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
