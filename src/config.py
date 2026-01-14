from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class IntegrationConfig:
    siga_base_url: str
    siga_auth_header: str
    siga_auth_token: str
    siga_auth_prefix: str
    siga_students_endpoint: str
    siga_boletos_endpoint: str
    siga_boletos_base_url: str
    siga_boletos_student_param: str
    siga_active_year: int
    siga_page_size: int
    siga_extra_headers: dict[str, str]
    megazap_base_url: str
    megazap_auth_header: str
    megazap_auth_token: str
    megazap_auth_prefix: str
    megazap_qrcode_endpoint: str
    megazap_default_message: str
    megazap_payload_template: dict[str, Any]

    @property
    def due_start(self) -> date:
        return date.today()

    @property
    def due_end(self) -> date:
        return date.today() + timedelta(days=5)


def _load_payload_template() -> dict[str, Any]:
    raw = os.getenv("MEGAZAP_PAYLOAD_TEMPLATE_JSON", "{}")
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "MEGAZAP_PAYLOAD_TEMPLATE_JSON must be valid JSON"
        ) from exc


def _load_siga_extra_headers() -> dict[str, str]:
    raw = os.getenv("SIGA_EXTRA_HEADERS_JSON", "{}")
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("SIGA_EXTRA_HEADERS_JSON must be valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("SIGA_EXTRA_HEADERS_JSON must be a JSON object")
    return {str(key): str(value) for key, value in data.items()}


def _load_env_default(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _load_env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def load_config(require_megazap_token: bool = True) -> IntegrationConfig:
    siga_base_url = _load_env_default("SIGA_BASE_URL", "https://siga04.activesoft.com.br/api")
    megazap_base_url = _load_env_default("MEGAZAP_BASE_URL", "https://api.megazap.com.br")

    siga_auth_token = _load_env_required("SIGA_AUTH_TOKEN")
    megazap_auth_token = os.getenv("MEGAZAP_AUTH_TOKEN", "").strip()
    if require_megazap_token and not megazap_auth_token:
        raise ValueError("MEGAZAP_AUTH_TOKEN is required")

    return IntegrationConfig(
        siga_base_url=siga_base_url.rstrip("/"),
        siga_auth_header=_load_env_default("SIGA_AUTH_HEADER", "Authorization"),
        siga_auth_token=siga_auth_token,
        siga_auth_prefix=_load_env_default("SIGA_AUTH_PREFIX", "Bearer"),
        siga_students_endpoint=_load_env_default("SIGA_STUDENTS_ENDPOINT", "/alunos"),
        siga_boletos_endpoint=_load_env_default(
            "SIGA_BOLETOS_ENDPOINT", "/alunos/{aluno_id}/boletos"
        ),
        siga_boletos_base_url=_load_env_default(
            "SIGA_BOLETOS_BASE_URL", siga_base_url
        ).rstrip("/"),
        siga_boletos_student_param=_load_env_default(
            "SIGA_BOLETOS_STUDENT_PARAM", "aluno_id"
        ),
        siga_active_year=int(os.getenv("SIGA_ACTIVE_YEAR", "2026")),
        siga_page_size=int(os.getenv("SIGA_PAGE_SIZE", "100")),
        siga_extra_headers=_load_siga_extra_headers(),
        megazap_base_url=megazap_base_url.rstrip("/"),
        megazap_auth_header=_load_env_default("MEGAZAP_AUTH_HEADER", "Authorization"),
        megazap_auth_token=megazap_auth_token,
        megazap_auth_prefix=_load_env_default("MEGAZAP_AUTH_PREFIX", "Bearer"),
        megazap_qrcode_endpoint=_load_env_default(
            "MEGAZAP_QRCODE_ENDPOINT", "/whatsapp/qrcode"
        ),
        megazap_default_message=os.getenv(
            "MEGAZAP_DEFAULT_MESSAGE",
            "Olá {nome}, seu boleto vence em {data_vencimento}. ",
        ),
        megazap_payload_template=_load_payload_template(),
    )
