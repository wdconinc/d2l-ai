from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from secrets import token_urlsafe
from threading import Lock


class LTIStateNonceStore:
    def __init__(self, ttl_seconds: int = 300, database_path: str = "") -> None:
        self.ttl_seconds = ttl_seconds
        self.database_path = database_path
        self._lock = Lock()
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._initialize()

    def issue(self) -> tuple[str, str]:
        with self._lock:
            self._cleanup_expired()
            state = token_urlsafe(32)
            nonce = token_urlsafe(32)
            expires_at = self._expiry_timestamp()
            with self._conn:
                self._conn.execute(
                    "INSERT INTO lti_states(state, nonce, expires_at) VALUES (?, ?, ?)",
                    (state, nonce, expires_at),
                )
        return state, nonce

    def consume(self, state: str, nonce: str) -> bool:
        with self._lock:
            self._cleanup_expired()
            with self._conn:
                row = self._conn.execute(
                    "SELECT nonce FROM lti_states WHERE state = ?",
                    (state,),
                ).fetchone()
                if row is None:
                    return False

                self._conn.execute("DELETE FROM lti_states WHERE state = ?", (state,))
                if row[0] != nonce:
                    return False

                nonce_exists = self._conn.execute(
                    "SELECT nonce FROM lti_used_nonces WHERE nonce = ?",
                    (nonce,),
                ).fetchone()
                if nonce_exists is not None:
                    return False

                self._conn.execute(
                    "INSERT INTO lti_used_nonces(nonce, expires_at) VALUES (?, ?)",
                    (nonce, self._expiry_timestamp()),
                )
                return True

    def _initialize(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lti_states (
                    state TEXT PRIMARY KEY,
                    nonce TEXT NOT NULL,
                    expires_at INTEGER NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lti_used_nonces (
                    nonce TEXT PRIMARY KEY,
                    expires_at INTEGER NOT NULL
                )
                """
            )

    def _cleanup_expired(self) -> None:
        now = self._now_timestamp()
        with self._conn:
            self._conn.execute("DELETE FROM lti_states WHERE expires_at < ?", (now,))
            self._conn.execute("DELETE FROM lti_used_nonces WHERE expires_at < ?", (now,))

    def _expiry_timestamp(self) -> int:
        return int((datetime.now(UTC) + timedelta(seconds=self.ttl_seconds)).timestamp())

    @staticmethod
    def _now_timestamp() -> int:
        return int(datetime.now(UTC).timestamp())
