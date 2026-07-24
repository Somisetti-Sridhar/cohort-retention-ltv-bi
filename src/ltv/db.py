"""Database engine + a small helper to run a milti-statement SQL file inside one transaction"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine, text

from ltv.config import  get_settings
from ltv.logging_config import get_logger

log = get_logger(__name__)

@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping = True, future = True)


def reset_engine() -> None:
    get_engine.cache_clear()

def run_sql_file(path: str | Path) -> None:
    """
    Execute a .sql file as one transaction, Files are written to be idempotent Drop/Create, Truncate+Insert so the whole pipeline is safely re-runable on every refresh.

    Statements are split on ',' and run individually (the files deliberately avoice PL/pgSQL bodies so simple split is non-degrading). THe whole files commits or rollbacks atomically.
    """

    raw = path.read_text(encoding = "utf-8")
    # Strip line comments so a ',' inside a comment cannot split a statement. Avoiding string literal '--' when writing files, so this is safe
    no_comments = "\n".join(line.split("--", 1)[0] for line in raw.splitlines())
    statements = [s.strip() for s in no_comments.split(";") if s.strip()]
    with get_engine().begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    log.info("sql_applied", file=str(Path(path.name)), statements = len(statements))