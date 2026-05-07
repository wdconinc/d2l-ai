"""Encrypted refresh token persistence for Brightspace OAuth2."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet


class EncryptedRefreshTokenStore:
    """Persist Brightspace refresh tokens encrypted at rest."""

    def __init__(self, db_path: str | Path, encryption_key: str) -> None:
        self._db_path = Path(db_path)
        self._cipher = Fernet(encryption_key.encode("utf-8"))
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_brightspace_tokens (
                    tenant TEXT NOT NULL,
                    token_owner TEXT NOT NULL,
                    refresh_token_encrypted TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (tenant, token_owner)
                )
                """
            )
            conn.commit()

    def save_refresh_token(self, tenant: str, token_owner: str, refresh_token: str) -> None:
        encrypted = self._cipher.encrypt(refresh_token.encode("utf-8")).decode("utf-8")
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO app_brightspace_tokens (
                    tenant,
                    token_owner,
                    refresh_token_encrypted,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(tenant, token_owner) DO UPDATE SET
                    refresh_token_encrypted = excluded.refresh_token_encrypted,
                    updated_at = excluded.updated_at
                """,
                (tenant, token_owner, encrypted, datetime.now(UTC).isoformat()),
            )
            conn.commit()

    def get_refresh_token(self, tenant: str, token_owner: str) -> str | None:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT refresh_token_encrypted
                FROM app_brightspace_tokens
                WHERE tenant = ? AND token_owner = ?
                """,
                (tenant, token_owner),
            ).fetchone()
        if row is None:
            return None
        return self._cipher.decrypt(row[0].encode("utf-8")).decode("utf-8")
