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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Integração SIGA -> MegaZap para boletos a vencer"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Não envia para o MegaZap, apenas loga o payload.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    config = load_config(require_megazap_token=not args.dry_run)
    run_integration(config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
