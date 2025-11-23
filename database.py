# database.py (ПЕРЕПИСАННЫЙ КОД ДЛЯ POSTGRESQL)

import asyncpg
from config import DATABASE_URL
from datetime import date, datetime, timedelta

# Глобальная переменная для пула подключений к PostgreSQL
pool = None


async def init_db():
    """Инициализирует пул подключений и создает все необходимые таблицы."""
    global pool

    # 1. Создаем пул подключений, используя URL из config.py
    if pool is None:
        pool = await asyncpg.create_pool(DATABASE_URL)

    # 2. Создаем таблицы
    async with pool.acquire() as conn:
        # Таблица users
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                partner_id BIGINT
            )
        """)
        # Таблица wishlist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS wishlist (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                text TEXT,
                photo_id TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        # Таблица surprises
        await conn.execute("""
               CREATE TABLE IF NOT EXISTS surprises (
                   id SERIAL PRIMARY KEY,
                   requester_id BIGINT,
                   partner_id BIGINT,
                   message TEXT,
                   delay_seconds INTEGER,
                   created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
               )
        """)
        # Таблица date_ideas
        await conn.execute("""
                CREATE TABLE IF NOT EXISTS date_ideas (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    used_count INTEGER DEFAULT 0
                )
        """)
        # Таблица date_history
        await conn.execute("""
                CREATE TABLE IF NOT EXISTS date_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    date_idea_id INTEGER,
                    month_start_date DATE,
                    deadline_date DATE
                )
        """)
        # Таблица important_dates
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS important_dates (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                partner_id BIGINT,
                title TEXT,
                event_date DATE,
                reminder_days INTEGER,
                reminded_at DATE
            )
        """)


# --- Функции для WishList и Users ---

async def save_wishlist(user_id, text, photo_id):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO wishlist (user_id, text, photo_id) VALUES ($1, $2, $3)",
            user_id, text, photo_id
        )


async def get_partner_id(user_id):
    async with pool.acquire() as conn:
        # fetchval используется для получения одного значения (partner_id)
        partner_id = await conn.fetchval(
            "SELECT partner_id FROM users WHERE id = $1", user_id
        )
        return partner_id


async def get_wishlist(user_id):
    async with pool.acquire() as conn:
        # fetch возвращает список объектов Record (кортежей)
        rows = await conn.fetch(
            "SELECT id, text, photo_id FROM wishlist WHERE user_id = $1", user_id
        )
        # Преобразуем объекты Record в простые кортежи, как раньше (id, text, photo_id)
        return [(row['id'], row['text'], row['photo_id']) for row in rows]


async def save_pair(user_id, partner_id):
    async with pool.acquire() as conn:
        # INSERT ... ON CONFLICT (id) DO UPDATE - аналог INSERT OR REPLACE в SQLite
        await conn.execute("""
            INSERT INTO users (id, partner_id) VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET partner_id = $2
        """, user_id, partner_id)


async def delete_wishlist_item(item_id, user_id):
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM wishlist WHERE id = $1 AND user_id = $2",
            item_id, user_id
        )


# --- Функции для Surprises ---

async def save_surprise(requester_id, partner_id, message, delay_seconds):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO surprises (requester_id, partner_id, message, delay_seconds) VALUES ($1, $2, $3, $4)",
            requester_id, partner_id, message, delay_seconds
        )


async def get_pending_surprises():
    async with pool.acquire() as conn:
        # Проверяем, что delay_seconds прошло с момента created_at
        rows = await conn.fetch("""
            SELECT id, partner_id, message
            FROM surprises
            WHERE created_at + interval '1 second' * delay_seconds <= NOW()
        """)
        return [(row['id'], row['partner_id'], row['message']) for row in rows]


async def delete_surprise(surprise_id):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM surprises WHERE id = $1", surprise_id)


# --- Функции для Date Ideas ---

async def save_date_idea(title, description):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO date_ideas (title, description) VALUES ($1, $2)",
            title, description
        )


async def get_all_unused_date_ideas():
    async with pool.acquire() as conn:
        # fetch возвращает список объектов Record (id, title, description)
        rows = await conn.fetch("SELECT id, title, description FROM date_ideas WHERE used_count = 0")
        return [(row['id'], row['title'], row['description']) for row in rows]


async def mark_date_idea_used(date_idea_id):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE date_ideas SET used_count = used_count + 1 WHERE id = $1",
            date_idea_id
        )


async def get_last_date_sender():
    async with pool.acquire() as conn:
        # Возвращает user_id, который последний отправил дату
        user_id = await conn.fetchval(
            "SELECT user_id FROM date_history ORDER BY id DESC LIMIT 1"
        )
        return user_id


async def get_all_paired_users():
    async with pool.acquire() as conn:
        # Возвращает список всех ID пользователей, у которых есть партнер
        rows = await conn.fetch("SELECT id FROM users WHERE partner_id IS NOT NULL")
        return [row['id'] for row in rows]


async def save_date_history(user_id, date_idea_id, month_start_date, deadline_date):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO date_history (user_id, date_idea_id, month_start_date, deadline_date) VALUES ($1, $2, $3, $4)",
            user_id, date_idea_id, month_start_date, deadline_date
        )


async def get_current_month_date_info():
    # Получаем информацию о текущем свидании месяца (если оно уже было назначено)
    from datetime import date
    # Используем to_char для сравнения только по месяцу и году, если 'day=15' — это ваша логика начала месяца
    current_month_start = date.today().replace(day=15).strftime('%Y-%m-%d')

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                dh.user_id, di.title, di.description, dh.deadline_date
            FROM date_history dh
            JOIN date_ideas di ON dh.date_idea_id = di.id
            WHERE dh.month_start_date = $1
            ORDER BY dh.id DESC LIMIT 1
        """, current_month_start)
        # Возвращаем кортеж (user_id, title, description, deadline_date)
        return (
        row['user_id'], row['title'], row['description'], row['deadline_date'].strftime('%Y-%m-%d')) if row else None


# --- Функции для Important Dates (Важных Дат) ---

async def save_important_date(user_id, partner_id, title, event_date_str, reminder_days):
    async with pool.acquire() as conn:
        # Преобразуем строку даты в объект date для PostgreSQL
        event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
        await conn.execute(
            "INSERT INTO important_dates (user_id, partner_id, title, event_date, reminder_days) VALUES ($1, $2, $3, $4, $5)",
            user_id, partner_id, title, event_date, reminder_days
        )


async def get_dates_for_reminder():
    # Проверяем, если до даты осталось reminder_days ИЛИ меньше,
    # и если напоминание не было отправлено сегодня (reminded_at IS NULL OR reminded_at < CURRENT_DATE)
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT user_id, partner_id, title, event_date, reminder_days
            FROM important_dates
            WHERE (event_date - CURRENT_DATE) <= reminder_days 
              AND (event_date - CURRENT_DATE) >= 0 
              AND (reminded_at IS NULL OR reminded_at < CURRENT_DATE)
        """)
        # Возвращаем список кортежей (user_id, partner_id, title, event_date, reminder_days)
        return [(row['user_id'], row['partner_id'], row['title'], row['event_date'].strftime('%Y-%m-%d'),
                 row['reminder_days']) for row in rows]


async def mark_date_reminded(user_id, title):
    async with pool.acquire() as conn:
        # Устанавливаем remind_at на сегодняшнюю дату (CURRENT_DATE)
        await conn.execute(
            "UPDATE important_dates SET reminded_at = CURRENT_DATE WHERE user_id = $1 AND title = $2",
            user_id, title
        )


async def get_all_important_dates(user_id, partner_id):
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, event_date, reminder_days
            FROM important_dates
            WHERE user_id = $1 OR partner_id = $2
            ORDER BY event_date ASC
        """, user_id, partner_id)
        # Преобразуем объекты Record в кортежи
        return [(row['id'], row['title'], row['event_date'].strftime('%Y-%m-%d'), row['reminder_days']) for row in rows]


async def delete_important_date(date_id, user_id):
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM important_dates WHERE id = $1 AND user_id = $2",
            date_id, user_id
        )