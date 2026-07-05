#!/usr/bin/env python3
"""Módulo de carga de referencias usando los PDFs de la carpeta de Seed para la plataforma Sales Qualification Agent."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

import requests


def _die(msg: str, code: int = 1) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    raise SystemExit(code)


def _load_json(path: Path) -> Any:
    if not path.exists():
        _die(f"No encuentro el fichero JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _post_reference(api_base: str, ref: Dict[str, Any], pdf_path: Path, timeout_s: int = 180) -> Dict[str, Any]:
    url = f"{api_base.rstrip('/')}/api/references"

    # Campos esperados por tu endpoint (Form + UploadFile)
    # Ajusta si tu API espera otros nombres exactos.
    data = {
        "title": ref["title"],
        "customer": ref["customer"],
        "industry": ref["industry"],
        "area": ref["area"],
        "cloud": ref["cloud"],
        "size": ref["size"],
    }

    with pdf_path.open("rb") as f:
        files = {
            "document": (pdf_path.name, f, "application/pdf")
        }
        resp = requests.post(url, data=data, files=files, timeout=timeout_s)

    # Manejo de errores detallado
    try:
        payload = resp.json()
    except Exception:
        payload = {"raw": resp.text}

    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code} - {payload}")

    return payload


def main() -> None:
    """Carga el catálogo base de referencias PDF y su metadata en el sistema."""
    parser = argparse.ArgumentParser(description="Seed de referencias (PDF + metadata) hacia FastAPI.")
    parser.add_argument("--api-base", default=os.getenv("API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--data-dir", default="seed_data", help="Directorio con references_metadata.json y subcarpeta pdfs/")
    parser.add_argument("--json", default="references_metadata.json")
    parser.add_argument("--pdf-dir", default="pdfs")
    parser.add_argument("--limit", type=int, default=0, help="0 = todas, N = solo N primeras")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    json_path = data_dir / args.json
    pdf_dir = data_dir / args.pdf_dir

    if not pdf_dir.exists():
        _die(f"No encuentro el directorio de PDFs: {pdf_dir}")

    items = _load_json(json_path)
    if not isinstance(items, list):
        _die("El JSON debe ser una lista de referencias.")

    if args.limit and args.limit > 0:
        items = items[: args.limit]

    print(f"[INFO] API: {args.api_base}")
    print(f"[INFO] JSON: {json_path}")
    print(f"[INFO] PDFs: {pdf_dir}")
    print(f"[INFO] Referencias a importar: {len(items)}")
    print("")

    ok = 0
    failed = 0

    for i, ref in enumerate(items, start=1):
        pdf_name = ref.get("document_path") or ref.get("pdf") or ref.get("document_file")
        if not pdf_name:
            print(f"[WARN] ({i}) Falta 'document_path' en JSON para: {ref.get('title')}")
            failed += 1
            continue

        pdf_path = pdf_dir / pdf_name
        if not pdf_path.exists():
            print(f"[WARN] ({i}) No existe el PDF: {pdf_path}")
            failed += 1
            continue

        title = ref.get("title", "Untitled")
        try:
            res = _post_reference(args.api_base, ref, pdf_path)
            ref_id = res.get("reference_id") or res.get("id") or "?"
            print(f"[OK]  ({i}) {title} -> reference_id={ref_id}  (indexing={res.get('indexing')})")
            ok += 1
        except Exception as e:
            print(f"[FAIL]({i}) {title} -> {e}")
            failed += 1

    print("")
    print(f"[DONE] OK={ok}  FAIL={failed}")
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()