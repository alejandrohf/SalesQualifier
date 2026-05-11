#!/usr/bin/env python3
"""Módulo `seed_data/scripts/seed_admin_user.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permite ejecutar este script directamente:
# python ./seed_data/scripts/seed_admin_user.py ...
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from domain.auth import hash_password
from infrastructure.db.users import (
    create_user,
    get_user_by_email,
    set_user_password,
    update_user,
)


def main() -> None:
    """Ejecuta `main` dentro de este modulo."""
    parser = argparse.ArgumentParser(description="Crea un usuario administrador inicial.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    if len(args.password) < 8:
        print("[ERROR] password debe tener al menos 8 caracteres", file=sys.stderr)
        raise SystemExit(1)

    existing = get_user_by_email(args.email)
    if existing:
        update_user(
            existing["id"],
            patch={
                "is_admin": True,
                "can_sales": False,
                "can_engineering": False,
                "is_active": True,
                "role": "admin",
            },
            updated_by=existing["id"],
        )
        set_user_password(
            existing["id"],
            password_hash=hash_password(args.password),
            updated_by=existing["id"],
        )
        print(f"[OK] Usuario existente actualizado: {args.email} (password reseteada).")
        return

    user = create_user(
        email=args.email,
        first_name=args.first_name,
        last_name=args.last_name,
        role=None,
        is_admin=True,
        can_sales=False,
        can_engineering=False,
        password_hash=hash_password(args.password),
        engineering_manager_id=None,
        created_by=None,
    )
    print(f"[OK] Usuario admin creado: {user['email']} (id={user['id']})")


if __name__ == "__main__":
    main()
