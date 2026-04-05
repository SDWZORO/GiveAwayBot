"""
SQLite Database Manager — async via aiosqlite.
Handles all database operations for the giveaway bot.
"""

import aiosqlite
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import DB_PATH

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Connect to SQLite and initialize tables."""
        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row
        await self.db.execute("PRAGMA journal_mode=WAL")
        await self.db.execute("PRAGMA foreign_keys=ON")
        await self._create_tables()
        logger.info("Database connected and tables initialized.")

    async def close(self):
        if self.db:
            await self.db.close()

    async def _create_tables(self):
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS giveaways (
                giveaway_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                reward TEXT NOT NULL,
                winners_count INTEGER NOT NULL DEFAULT 1,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                ended_at TEXT,
                target_chats TEXT DEFAULT '[]',
                join_requirements TEXT DEFAULT '[]',
                language_code TEXT DEFAULT 'en',
                manual_end INTEGER DEFAULT 0,
                announcement_message_ids TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS participants (
                giveaway_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                joined_at TEXT NOT NULL,
                boost_weight REAL DEFAULT 0.0,
                manual_selected INTEGER DEFAULT 0,
                verified INTEGER DEFAULT 1,
                source TEXT DEFAULT 'dm',
                language_code TEXT DEFAULT 'en',
                PRIMARY KEY (giveaway_id, user_id),
                FOREIGN KEY (giveaway_id) REFERENCES giveaways(giveaway_id)
            );

            CREATE TABLE IF NOT EXISTS bans (
                user_id INTEGER PRIMARY KEY,
                reason TEXT DEFAULT '',
                banned_by INTEGER NOT NULL,
                banned_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS history (
                giveaway_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                reward TEXT NOT NULL,
                participants_count INTEGER DEFAULT 0,
                winner_ids TEXT DEFAULT '[]',
                winner_usernames TEXT DEFAULT '[]',
                status TEXT NOT NULL,
                ended_by INTEGER,
                finalized_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                language_code TEXT DEFAULT 'en'
            );

            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER PRIMARY KEY,
                joined_count INTEGER DEFAULT 0,
                won_count INTEGER DEFAULT 0,
                last_joined TEXT,
                last_won TEXT
            );

            CREATE TABLE IF NOT EXISTS owner_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                actor_id INTEGER NOT NULL,
                target_id INTEGER,
                giveaway_id TEXT,
                timestamp TEXT NOT NULL,
                details TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        await self.db.commit()

    # ─── Config ───

    async def get_config(self, key: str, default: str = "") -> str:
        async with self.db.execute("SELECT value FROM config WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else default

    async def set_config(self, key: str, value: str):
        await self.db.execute(
            "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, value, value)
        )
        await self.db.commit()

    # ─── User Settings ───

    async def get_user_language(self, user_id: int) -> str:
        async with self.db.execute(
            "SELECT language_code FROM user_settings WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else "en"

    async def set_user_language(self, user_id: int, lang: str):
        await self.db.execute(
            "INSERT INTO user_settings (user_id, language_code) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET language_code = ?",
            (user_id, lang, lang)
        )
        await self.db.commit()

    # ─── Giveaways ───

    async def create_giveaway(self, data: Dict[str, Any]):
        await self.db.execute(
            """INSERT INTO giveaways
            (giveaway_id, title, reward, winners_count, start_time, end_time,
             status, created_by, created_at, target_chats, join_requirements, language_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["giveaway_id"], data["title"], data["reward"],
                data["winners_count"], data["start_time"], data["end_time"],
                data.get("status", "scheduled"), data["created_by"],
                datetime.now().isoformat(),
                json.dumps(data.get("target_chats", [])),
                json.dumps(data.get("join_requirements", [])),
                data.get("language_code", "en"),
            )
        )
        await self.db.commit()

    async def get_active_giveaway(self) -> Optional[Dict]:
        async with self.db.execute(
            "SELECT * FROM giveaways WHERE status IN ('active', 'scheduled') ORDER BY created_at DESC LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)
            return None

    async def get_giveaway(self, giveaway_id: str) -> Optional[Dict]:
        async with self.db.execute(
            "SELECT * FROM giveaways WHERE giveaway_id = ?", (giveaway_id,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)
            return None

    async def update_giveaway_status(self, giveaway_id: str, status: str, ended_at: str = None):
        if ended_at:
            await self.db.execute(
                "UPDATE giveaways SET status = ?, ended_at = ? WHERE giveaway_id = ?",
                (status, ended_at, giveaway_id)
            )
        else:
            await self.db.execute(
                "UPDATE giveaways SET status = ? WHERE giveaway_id = ?",
                (status, giveaway_id)
            )
        await self.db.commit()

    async def save_announcement_ids(self, giveaway_id: str, msg_ids: Dict):
        await self.db.execute(
            "UPDATE giveaways SET announcement_message_ids = ? WHERE giveaway_id = ?",
            (json.dumps(msg_ids), giveaway_id)
        )
        await self.db.commit()

    # ─── Participants ───

    async def add_participant(self, data: Dict[str, Any]):
        await self.db.execute(
            """INSERT INTO participants
            (giveaway_id, user_id, username, full_name, joined_at, boost_weight,
             verified, source, language_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["giveaway_id"], data["user_id"], data.get("username", ""),
                data.get("full_name", ""), datetime.now().isoformat(),
                data.get("boost_weight", 0.0), 1, data.get("source", "dm"),
                data.get("language_code", "en"),
            )
        )
        await self.db.commit()

    async def is_participant(self, giveaway_id: str, user_id: int) -> bool:
        async with self.db.execute(
            "SELECT 1 FROM participants WHERE giveaway_id = ? AND user_id = ?",
            (giveaway_id, user_id)
        ) as cur:
            return await cur.fetchone() is not None

    async def get_participants(self, giveaway_id: str) -> List[Dict]:
        async with self.db.execute(
            "SELECT * FROM participants WHERE giveaway_id = ? ORDER BY joined_at",
            (giveaway_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def get_participant_count(self, giveaway_id: str) -> int:
        async with self.db.execute(
            "SELECT COUNT(*) FROM participants WHERE giveaway_id = ?",
            (giveaway_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0]

    async def remove_participant(self, giveaway_id: str, user_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM participants WHERE giveaway_id = ? AND user_id = ?",
            (giveaway_id, user_id)
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def set_participant_boost(self, giveaway_id: str, user_id: int, boost: float) -> bool:
        cursor = await self.db.execute(
            "UPDATE participants SET boost_weight = ? WHERE giveaway_id = ? AND user_id = ?",
            (boost, giveaway_id, user_id)
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def set_manual_winner(self, giveaway_id: str, user_id: int) -> bool:
        cursor = await self.db.execute(
            "UPDATE participants SET manual_selected = 1 WHERE giveaway_id = ? AND user_id = ?",
            (giveaway_id, user_id)
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def get_boosted_count(self, giveaway_id: str) -> int:
        async with self.db.execute(
            "SELECT COUNT(*) FROM participants WHERE giveaway_id = ? AND boost_weight > 0",
            (giveaway_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0]

    # ─── Bans ───

    async def is_banned(self, user_id: int) -> bool:
        async with self.db.execute(
            "SELECT 1 FROM bans WHERE user_id = ?", (user_id,)
        ) as cur:
            return await cur.fetchone() is not None

    async def ban_user(self, user_id: int, reason: str, banned_by: int) -> bool:
        try:
            await self.db.execute(
                "INSERT INTO bans (user_id, reason, banned_by, banned_at) VALUES (?, ?, ?, ?)",
                (user_id, reason, banned_by, datetime.now().isoformat())
            )
            await self.db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def get_ban_count(self) -> int:
        async with self.db.execute("SELECT COUNT(*) FROM bans") as cur:
            row = await cur.fetchone()
            return row[0]

    # ─── History ───

    async def save_history(self, data: Dict[str, Any]):
        await self.db.execute(
            """INSERT OR REPLACE INTO history
            (giveaway_id, title, reward, participants_count, winner_ids,
             winner_usernames, status, ended_by, finalized_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["giveaway_id"], data["title"], data["reward"],
                data["participants_count"], json.dumps(data.get("winner_ids", [])),
                json.dumps(data.get("winner_usernames", [])), data["status"],
                data.get("ended_by"), datetime.now().isoformat(),
            )
        )
        await self.db.commit()

    async def get_history(self) -> List[Dict]:
        async with self.db.execute(
            "SELECT * FROM history ORDER BY finalized_at DESC"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    # ─── User Stats ───

    async def update_user_stats_join(self, user_id: int):
        now = datetime.now().isoformat()
        await self.db.execute(
            """INSERT INTO user_stats (user_id, joined_count, won_count, last_joined)
            VALUES (?, 1, 0, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            joined_count = joined_count + 1, last_joined = ?""",
            (user_id, now, now)
        )
        await self.db.commit()

    async def update_user_stats_win(self, user_id: int):
        now = datetime.now().isoformat()
        await self.db.execute(
            """INSERT INTO user_stats (user_id, joined_count, won_count, last_won)
            VALUES (?, 0, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            won_count = won_count + 1, last_won = ?""",
            (user_id, now, now)
        )
        await self.db.commit()

    async def get_user_stats(self, user_id: int) -> Optional[Dict]:
        async with self.db.execute(
            "SELECT * FROM user_stats WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)
            return None

    # ─── Broadcast ───

    async def get_all_dm_user_ids(self) -> List[int]:
        """Get all unique user IDs the bot has interacted with (for DM broadcast)."""
        async with self.db.execute(
            """SELECT DISTINCT user_id FROM (
                SELECT user_id FROM participants
                UNION
                SELECT user_id FROM user_settings
                UNION
                SELECT user_id FROM user_stats
            )"""
        ) as cur:
            rows = await cur.fetchall()
            return [row[0] for row in rows]

    # ─── Owner Logs ───

    async def add_log(self, action: str, actor_id: int, target_id: int = None,
                      giveaway_id: str = None, details: str = ""):
        await self.db.execute(
            """INSERT INTO owner_logs (action, actor_id, target_id, giveaway_id, timestamp, details)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (action, actor_id, target_id, giveaway_id, datetime.now().isoformat(), details)
        )
        await self.db.commit()


# Singleton
db = Database()
