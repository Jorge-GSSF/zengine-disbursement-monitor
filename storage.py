from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class Storage:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.is_postgres = database_url.startswith(("postgres://", "postgresql://"))
        self.sqlite_path = self._sqlite_path(database_url)

    def init(self) -> None:
        if self.is_postgres:
            with self._pg_connection() as conn:
                conn.execute(
                    """
                    create table if not exists notified_records (
                        record_id text primary key,
                        status_value text not null,
                        notified_at timestamptz not null default now()
                    )
                    """
                )
                conn.execute(
                    """
                    create table if not exists monitor_state (
                        key text primary key,
                        value text not null,
                        updated_at timestamptz not null default now()
                    )
                    """
                )
                conn.commit()
            return

        assert self.sqlite_path is not None
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        with self._sqlite_connection() as conn:
            conn.execute(
                """
                create table if not exists notified_records (
                    record_id text primary key,
                    status_value text not null,
                    notified_at text not null default current_timestamp
                )
                """
            )
            conn.execute(
                """
                create table if not exists monitor_state (
                    key text primary key,
                    value text not null,
                    updated_at text not null default current_timestamp
                )
                """
            )

    def has_notified(self, record_id: str) -> bool:
        if self.is_postgres:
            with self._pg_connection() as conn:
                row = conn.execute(
                    "select 1 from notified_records where record_id = %s",
                    (record_id,),
                ).fetchone()
                return row is not None
        with self._sqlite_connection() as conn:
            row = conn.execute(
                "select 1 from notified_records where record_id = ?",
                (record_id,),
            ).fetchone()
            return row is not None

    def mark_notified(self, record_id: str, status_value: str) -> None:
        if self.is_postgres:
            with self._pg_connection() as conn:
                conn.execute(
                    """
                    insert into notified_records (record_id, status_value)
                    values (%s, %s)
                    on conflict (record_id) do nothing
                    """,
                    (record_id, status_value),
                )
                conn.commit()
            return
        with self._sqlite_connection() as conn:
            conn.execute(
                """
                insert or ignore into notified_records (record_id, status_value)
                values (?, ?)
                """,
                (record_id, status_value),
            )

    def get_state(self, key: str) -> str | None:
        if self.is_postgres:
            with self._pg_connection() as conn:
                row = conn.execute(
                    "select value from monitor_state where key = %s",
                    (key,),
                ).fetchone()
                return str(row["value"]) if row else None
        with self._sqlite_connection() as conn:
            row = conn.execute(
                "select value from monitor_state where key = ?",
                (key,),
            ).fetchone()
            return str(row["value"]) if row else None

    def set_state(self, key: str, value: str) -> None:
        if self.is_postgres:
            with self._pg_connection() as conn:
                conn.execute(
                    """
                    insert into monitor_state (key, value, updated_at)
                    values (%s, %s, now())
                    on conflict (key) do update
                    set value = excluded.value, updated_at = now()
                    """,
                    (key, value),
                )
                conn.commit()
            return
        with self._sqlite_connection() as conn:
            conn.execute(
                """
                insert into monitor_state (key, value, updated_at)
                values (?, ?, current_timestamp)
                on conflict(key) do update
                set value = excluded.value, updated_at = current_timestamp
                """,
                (key, value),
            )

    @contextmanager
    def _pg_connection(self) -> Iterator[object]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            yield conn

    @contextmanager
    def _sqlite_connection(self) -> Iterator[sqlite3.Connection]:
        assert self.sqlite_path is not None
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _sqlite_path(database_url: str) -> Path | None:
        if database_url.startswith("sqlite:///"):
            return Path(database_url.removeprefix("sqlite:///"))
        if database_url == "sqlite:///:memory:":
            return Path(":memory:")
        if "://" not in database_url:
            return Path(database_url)
        if database_url.startswith(("postgres://", "postgresql://")):
            return None
        raise ValueError(f"Unsupported DATABASE_URL: {database_url}")
