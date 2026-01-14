from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
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
        headers = {
            "Accept": "application/json",
            self._config.siga_auth_header: f"{prefix} {token}".strip(),
        }
        headers.update(self._config.siga_extra_headers)
        return headers

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

    def _parse_date(self, value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                return None

    def get_boletos_due(self, aluno_id: str, start: date, end: date) -> list[Boleto]:
        endpoint = self._config.siga_boletos_endpoint.format(aluno_id=aluno_id)
        params = {
            self._config.siga_boletos_student_param: aluno_id,
            "dataVencimentoInicio": start.isoformat(),
            "dataVencimentoFim": end.isoformat(),
        }
        url = urljoin(self._config.siga_boletos_base_url, endpoint)
        response = self._session.get(url, headers=self._headers(), params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items") or payload.get("data") or payload.get("resultados") or []
        boletos: list[Boleto] = []
        for item in items:
            due_date = self._parse_date(item.get("dataVencimento") or item.get("dt_vencimento"))
            if not due_date:
                continue
            if due_date < start or due_date > end:
                continue
            boletos.append(
                Boleto(
                    id=str(item.get("id") or item.get("codigo") or ""),
                    due_date=due_date,
                    amount=float(
                        item.get("valor")
                        or item.get("valor_recebido_total")
                        or item.get("valor_boleto")
                        or 0
                    ),
                    barcode=item.get("codigoBarras") or item.get("codigo_barras") or "",
                    line_digit=item.get("linhaDigitavel") or item.get("linha_digitavel") or "",
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
