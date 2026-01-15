from __future__ import annotations

import argparse
import copy
import logging
from dataclasses import asdict
from datetime import date
from typing import Any

from .clients import MegaZapClient, SIGAClient
from .config import IntegrationConfig, load_config

logger = logging.getLogger(__name__)


def build_megazap_payload(
    config: IntegrationConfig,
    aluno: dict[str, Any],
    boleto: dict[str, Any],
) -> dict[str, Any]:
    payload = copy.deepcopy(config.megazap_payload_template)
    payload.setdefault("telefone", aluno.get("phone"))
    payload.setdefault(
        "mensagem",
        config.megazap_default_message.format(
            nome=aluno.get("name"),
            data_vencimento=boleto.get("due_date"),
        ),
    )
    payload.setdefault("valor", boleto.get("amount"))
    payload.setdefault("codigoBarras", boleto.get("barcode"))
    payload.setdefault("linhaDigitavel", boleto.get("line_digit"))
    payload.setdefault("dataVencimento", boleto.get("due_date"))
    return payload


def _safe_student(student: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": student.get("id"),
        "name": student.get("name"),
        "phone": student.get("phone"),
    }


def _safe_boleto(boleto: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": boleto.get("id"),
        "due_date": boleto.get("due_date"),
        "amount": boleto.get("amount"),
        "barcode": boleto.get("barcode"),
        "line_digit": boleto.get("line_digit"),
    }


def run_integration(config: IntegrationConfig, dry_run: bool = False) -> None:
    siga_client = SIGAClient(config)
    megazap_client = MegaZapClient(config)

    for student in siga_client.iter_active_students(config.siga_active_year):
        if not student.id:
            logger.warning("Aluno sem ID foi ignorado: %s", student)
            continue

        boletos = siga_client.get_boletos_due(
            student.id, config.due_start, config.due_end
        )
        if not boletos:
            continue

        for boleto in boletos:
            aluno_data = _safe_student(asdict(student))
            boleto_data = _safe_boleto(asdict(boleto))
            payload = build_megazap_payload(config, aluno_data, boleto_data)
            if dry_run:
                logger.info("Dry-run envio MegaZap: %s", payload)
                continue

            response = megazap_client.send_qrcode(payload)
            logger.info(
                "MegaZap enviado aluno=%s boleto=%s resposta=%s",
                student.id,
                boleto.id,
                response,
            )


def _redact_value(value: str, visible: int = 4) -> str:
    if not value:
        return "<vazio>"
    if len(value) <= visible:
        return "***"
    return f"{value[:2]}...{value[-visible:]}"


def _redact_authorization(value: str) -> str:
    if not value:
        return "<vazio>"
    parts = value.split(" ", 1)
    if len(parts) == 2:
        prefix, token = parts
        return f"{prefix} {_redact_value(token)}"
    return _redact_value(value)


def debug_siga(config: IntegrationConfig) -> None:
    siga_client = SIGAClient(config)
    url, headers, params = siga_client.build_students_request(config.siga_active_year, page=1)

    redacted_headers = {}
    for key, value in headers.items():
        if key.lower() == config.siga_auth_header.lower():
            redacted_headers[key] = _redact_authorization(value)
        else:
            redacted_headers[key] = "<redacted>"

    logger.info("SIGA debug URL: %s", url)
    logger.info("SIGA debug params: %s", params)
    logger.info("SIGA debug headers: %s", redacted_headers)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Integração SIGA -> MegaZap para boletos a vencer"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Não envia para o MegaZap, apenas loga o payload.",
    )
    parser.add_argument(
        "--debug-siga",
        action="store_true",
        help="Exibe URL, parâmetros e headers (com token ofuscado) usados no SIGA.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Atalho para --debug-siga.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    debug_mode = args.debug_siga or args.debug
    config = load_config(require_megazap_token=not (args.dry_run or debug_mode))
    if debug_mode:
        debug_siga(config)
        return
    run_integration(config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
