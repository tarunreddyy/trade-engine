import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from trade_engine.config.trading_config import get_order_journal_file


class OrderJournal:
    """Persistent SQLite journal for order lifecycle tracking."""

    FINAL_STATUSES = {"FILLED", "COMPLETE", "CANCELLED", "REJECTED", "FAILED"}

    def __init__(self, db_file: Optional[str] = None):
        self.db_file = db_file or get_order_journal_file()
        self._init_db()

    def _connect(self):
        path = Path(self.db_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(path))

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT,
                    broker_order_id TEXT,
                    broker_payload TEXT,
                    is_exit INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_orders_status_mode ON orders(status, mode);"
            )
            conn.commit()

    def record_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        mode: str,
        status: str,
        reason: str = "",
        broker_order_id: str = "",
        broker_payload: Optional[Dict[str, Any]] = None,
        is_exit: bool = False,
    ) -> int:
        now = datetime.utcnow().isoformat()
        payload = json.dumps(broker_payload or {}, default=str)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO orders (
                    created_at, updated_at, symbol, side, quantity, price, mode, status, reason,
                    broker_order_id, broker_payload, is_exit
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    now,
                    symbol.upper(),
                    side.upper(),
                    int(quantity),
                    float(price),
                    mode.lower(),
                    status.upper(),
                    reason,
                    broker_order_id or "",
                    payload,
                    1 if is_exit else 0,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def update_order(
        self,
        journal_id: int,
        status: str,
        reason: str = "",
        broker_payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        now = datetime.utcnow().isoformat()
        payload = json.dumps(broker_payload or {}, default=str)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE orders
                SET updated_at = ?, status = ?, reason = ?, broker_payload = ?
                WHERE id = ?
                """,
                (now, status.upper(), reason, payload, int(journal_id)),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_open_live_orders(self, limit: int = 200) -> List[Dict[str, Any]]:
        statuses = ("SENT", "OPEN", "PARTIAL")
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, symbol, side, quantity, price, mode, status, reason, broker_order_id, is_exit
                FROM orders
                WHERE mode = 'live' AND status IN (?, ?, ?)
                ORDER BY id DESC
                LIMIT ?
                """,
                (*statuses, int(limit)),
            ).fetchall()

        result = []
        for row in rows:
            result.append(
                {
                    "id": int(row[0]),
                    "symbol": row[1],
                    "side": row[2],
                    "quantity": int(row[3]),
                    "price": float(row[4]),
                    "mode": row[5],
                    "status": row[6],
                    "reason": row[7] or "",
                    "broker_order_id": row[8] or "",
                    "is_exit": bool(row[9]),
                }
            )
        return result
