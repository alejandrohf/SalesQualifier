#!/usr/bin/env python3
"""Módulo `seed_data/scripts/seed_qualifications.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import requests


CLIENTS = [
    ("GlobalFleet Logistics Group", "https://globalfleetlogistics.com", "transport"),
    ("NovaRetail Iberia", "https://novaretail.example.com", "retail"),
    ("MediCore Health Systems", "https://medicore.example.com", "health"),
    ("UrbanGrid Energy", "https://urbangrid.example.com", "energy"),
    ("AeroDynamics Europe", "https://aerodynamics.example.com", "aerospace"),
    ("FinTrust Capital", "https://fintrust.example.com", "finance"),
]

REQUESTERS = [
    ("Laura Sánchez", "decision_maker", "director"),
    ("Miguel Romero", "decision_maker", "vp_head"),
    ("Marina López", "non_decision_maker", "employee"),
    ("Javier Ortega", "decision_maker", "cxo"),
]

COLLABORATIONS = ["t&m", "fixed_price", "profiles_request", "rfp", "consulting", "licenses", "other"]
PARTNERS = ["none", "microsoft", "aws", "google", "ibm", "multiverse", "snowflake", "databricks", "other"]
AREAS = ["data", "ai", "security", "infrastructure", "other"]
DEAL_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
CONFIDENCE = ["Alta", "Media", "Baja", "No sabe"]


def _die(msg: str, code: int = 1) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    raise SystemExit(code)


def _build_description(client_name: str, sector: str, area: str, partner: str) -> str:
    return (
        f"{client_name} quiere acelerar su transformación en {sector} con una iniciativa de {area}. "
        f"Se plantea modernizar arquitectura, gobierno de datos y capacidades de IA, con integración de sistemas legacy "
        f"y despliegue cloud con partner {partner}. Objetivos: reducir costes operativos, mejorar tiempos de respuesta "
        f"y crear una base escalable para nuevos servicios. Se requiere propuesta técnica y económica con roadmap por fases."
    )


def _build_payload(i: int, rnd: random.Random, force_needs_date: bool | None = None) -> Dict[str, Any]:
    client_name, website, sector = rnd.choice(CLIENTS)
    req_name, req_role, req_seniority = rnd.choice(REQUESTERS)
    collaboration = rnd.choice(COLLABORATIONS)
    partner = rnd.choice(PARTNERS)
    area = rnd.choice(AREAS)
    deal_size = rnd.choice(DEAL_SIZES)
    needs_date = rnd.choice([True, False]) if force_needs_date is None else bool(force_needs_date)
    proposal_due_date = None
    if needs_date:
        # Fecha límite en próximas semanas (1 a 8), con hora laboral
        weeks_ahead = rnd.randint(1, 8)
        days_extra = rnd.randint(0, 6)
        due_dt = datetime.now(timezone.utc) + timedelta(weeks=weeks_ahead, days=days_extra)
        due_dt = due_dt.replace(hour=rnd.choice([9, 10, 11, 16, 17, 18]), minute=rnd.choice([0, 15, 30, 45]), second=0, microsecond=0)
        proposal_due_date = due_dt.isoformat()

    payload: Dict[str, Any] = {
        "client_name": f"{client_name} #{i+1}",
        "is_new_client": rnd.choice([True, False]),
        "client_website": website,
        "requester": {
            "name": req_name,
            "role": req_role,
            "seniority": req_seniority,
        },
        "description": _build_description(client_name, sector, area, partner),
        "quote_id": f"QUO-{i+1:05d}",
        "quote_crm_url": f"https://crm.example.com/opportunity/{i+1}",
        "shared_folder_url": f"https://share.example.com/folder/{i+1}",
        "collaboration_type": collaboration,
        "partner": partner,
        "main_area": area,
        "relationship_trust": rnd.randint(1, 5),
        "sales_confidence": rnd.choice(CONFIDENCE),
        "needs_date": needs_date,
        "deal_size": deal_size,
        "notes": (
            "Seed automático para pruebas E2E de cualificación. "
            "Validar scoring, referencias, notificación y persistencia."
        ),
    }
    if proposal_due_date:
        payload["proposal_due_date"] = proposal_due_date
    return payload


def _post_qualify(api_base: str, payload: Dict[str, Any], timeout_s: int) -> Dict[str, Any]:
    url = f"{api_base.rstrip('/')}/api/qualify"
    body = {"opportunity": payload, "metadata": {}}
    resp = requests.post(url, json=body, timeout=timeout_s)
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code} - {data}")
    return data


def main() -> None:
    """Ejecuta `main` dentro de este modulo."""
    parser = argparse.ArgumentParser(description="Genera cualificaciones de prueba y llama a /api/qualify.")
    parser.add_argument("--api-base", default=os.getenv("API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--count", type=int, default=20, help="Número de oportunidades a generar")
    parser.add_argument("--seed", type=int, default=42, help="Semilla para reproducibilidad")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout por request (segundos)")
    parser.add_argument("--delay-ms", type=int, default=300, help="Delay entre requests en ms")
    parser.add_argument(
        "--with-date-ratio",
        type=float,
        default=0.4,
        help="Proporción [0..1] de oportunidades con needs_date=true (default 0.4)",
    )
    parser.add_argument("--dry-run", action="store_true", help="No llama API; imprime payloads")
    args = parser.parse_args()

    if args.count <= 0:
        _die("--count debe ser > 0")
    if args.with_date_ratio < 0 or args.with_date_ratio > 1:
        _die("--with-date-ratio debe estar entre 0 y 1")

    rnd = random.Random(args.seed)
    print(f"[INFO] API: {args.api_base}")
    print(
        f"[INFO] count={args.count} seed={args.seed} timeout={args.timeout}s "
        f"delay={args.delay_ms}ms with_date_ratio={args.with_date_ratio} dry_run={args.dry_run}"
    )
    print("")

    target_with_date = int(round(args.count * args.with_date_ratio))
    indices_with_date = set(rnd.sample(range(args.count), k=target_with_date)) if target_with_date > 0 else set()

    ok = 0
    fail = 0
    for i in range(args.count):
        payload = _build_payload(i, rnd, force_needs_date=(i in indices_with_date))
        title = payload["client_name"]
        if args.dry_run:
            print(f"[DRY] ({i+1}) {title}")
            print(json.dumps(payload, ensure_ascii=False))
            ok += 1
            continue
        try:
            res = _post_qualify(args.api_base, payload, timeout_s=args.timeout)
            opp_id = res.get("opportunity_id", "?")
            status = res.get("status", "?")
            print(f"[OK]  ({i+1}) {title} -> opportunity_id={opp_id} status={status}")
            ok += 1
        except Exception as e:
            print(f"[FAIL]({i+1}) {title} -> {e}")
            fail += 1
        time.sleep(max(0, args.delay_ms) / 1000.0)

    print("")
    print(f"[DONE] OK={ok} FAIL={fail}")
    if fail:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
