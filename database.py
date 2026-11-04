import aiosqlite
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = "bot_database.db"

async def init_db():
    """Инициализация базы данных и создание таблиц."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                has_avatar INTEGER DEFAULT 0,
                avatar_file_id TEXT,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                visits_count INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                sender TEXT, -- 'user' или 'bot'
                text TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        await db.execute("DROP VIEW IF EXISTS top_active_users")
        await db.execute("""
            CREATE VIEW top_active_users AS
            SELECT u.user_id, u.username, u.first_name, u.last_name,
                   u.visits_count, u.last_seen, u.first_seen,
                   (SELECT COUNT(*) FROM messages m WHERE m.user_id = u.user_id) AS messages_count
            FROM users u
            ORDER BY u.visits_count DESC, u.last_seen DESC
            LIMIT 5
        """)
        await db.commit()
    logger.info("База данных SQLite успешно инициализирована (users, messages, top_active_users).")

async def save_message(user_id: int, sender: str, text: Optional[str]):
    """
    Сохраняет сообщение в историю чата.
    sender: 'user' или 'bot'
    """
    if not text:
        return
    now = datetime.utcnow().isoformat()
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO messages (user_id, sender, text, timestamp)
                VALUES (?, ?, ?, ?)
            """, (user_id, sender, text, now))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка сохранения сообщения в БД: {e}")

async def get_chat_history(user_id: int, limit: int = 50) -> list:
    """Получает последние сообщения пользователя и бота."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, user_id, sender, text, timestamp
            FROM messages
            WHERE user_id = ?
            ORDER BY id ASC
            LIMIT ?
        """, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def register_or_update_user(
    user_id: int,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    has_avatar: bool = False,
    avatar_file_id: Optional[str] = None
) -> Tuple[bool, int]:
    """
    Регистрирует нового пользователя или обновляет существующего.
    Возвращает кортеж: (is_new_user: bool, visits_count: int)
    """
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT visits_count FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()

        if row is None:
            # Новый пользователь
            await db.execute("""
                INSERT INTO users (
                    user_id, username, first_name, last_name,
                    has_avatar, avatar_file_id, first_seen, last_seen, visits_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (user_id, username, first_name, last_name, int(has_avatar), avatar_file_id, now, now))
            await db.commit()
            return True, 1
        else:
            # Повторный визит
            visits_count = row[0] + 1
            await db.execute("""
                UPDATE users
                SET username = ?,
                    first_name = ?,
                    last_name = ?,
                    has_avatar = ?,
                    avatar_file_id = ?,
                    last_seen = ?,
                    visits_count = ?
                WHERE user_id = ?
            """, (username, first_name, last_name, int(has_avatar), avatar_file_id, now, visits_count, user_id))
            await db.commit()
            return False, visits_count

async def get_top_active_users(limit: int = 5) -> list:
    """Возвращает топ активных пользователей по количеству визитов."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT u.user_id, u.username, u.first_name, u.last_name,
                   u.visits_count, u.first_seen, u.last_seen,
                   (SELECT COUNT(*) FROM messages m WHERE m.user_id = u.user_id) AS messages_count
            FROM users u
            ORDER BY u.visits_count DESC, u.last_seen DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
