import aiosqlite

DB_NAME = "wishlist.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            partner_id INTEGER
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            photo_id TEXT,
            created_at TEXT
        )""")
        await db.execute("""
               CREATE TABLE IF NOT EXISTS surprises (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   requester_id INTEGER,
                   partner_id INTEGER,
                   message TEXT,
                   delay_seconds INTEGER,
                   created_at TEXT
               )""")
        await db.execute("""
                CREATE TABLE IF NOT EXISTS date_ideas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    used_count INTEGER DEFAULT 0
                )""")

        # НОВАЯ ТАБЛИЦА: История свиданий (для чередования и срока)
        await db.execute("""
                CREATE TABLE IF NOT EXISTS date_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date_idea_id INTEGER,
                    month_start_date TEXT, -- Дата начала месяца (для отслеживания)
                    deadline_date TEXT,    -- Срок выполнения
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(date_idea_id) REFERENCES date_ideas(id)
                )""")
        await db.execute("""
                CREATE TABLE IF NOT EXISTS important_dates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    partner_id INTEGER,
                    title TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    reminder_days INTEGER,
                    reminded_at TEXT
                )""")
        await db.commit()


async def save_wishlist(user_id, text, photo_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO wishlist (user_id, text, photo_id, created_at) VALUES (?, ?, ?, datetime('now'))",
            (user_id, text, photo_id)
        )
        await db.commit()

async def get_partner_id(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT partner_id FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else None

async def get_wishlist(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, text, photo_id FROM wishlist WHERE user_id = ?", (user_id,))
        return await cursor.fetchall()

async def save_pair(user_id, partner_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO users (id, partner_id) VALUES (?, ?)", (user_id, partner_id))
        await db.commit()

async def delete_wishlist_item(item_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM wishlist WHERE id = ? AND user_id = ?", (item_id, user_id))
        await db.commit()
async def save_surprise(requester_id, partner_id, message, delay_seconds):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO surprises (requester_id, partner_id, message, delay_seconds, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (requester_id, partner_id, message, delay_seconds)
        )
        await db.commit()


async def save_date_idea(title, description):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO date_ideas (title, description) VALUES (?, ?)",
            (title, description)
        )
        await db.commit()


async def get_all_unused_date_ideas():
    # Получаем идеи, которые использовались наименьшее количество раз
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, title, description FROM date_ideas ORDER BY used_count ASC")
        return await cursor.fetchall()


async def mark_date_idea_used(idea_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE date_ideas SET used_count = used_count + 1 WHERE id = ?",
            (idea_id,)
        )
        await db.commit()


async def get_last_date_sender():
    # Определяем, кто последний получил идею (т.е., кто должен получить в этот раз)
    async with aiosqlite.connect(DB_NAME) as db:
        # Находим последнюю отправленную запись в истории за текущий месяц
        cursor = await db.execute(
            "SELECT user_id FROM date_history ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def save_date_history(user_id, date_idea_id, month_start_date, deadline_date):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO date_history (user_id, date_idea_id, month_start_date, deadline_date) VALUES (?, ?, ?, ?)",
            (user_id, date_idea_id, month_start_date, deadline_date)
        )
        await db.commit()


async def get_current_month_date_info():
    # Получаем информацию о текущем свидании месяца (если оно уже было назначено)
    # Ищем запись, соответствующую текущему 15-му числу (началу месяца)
    from datetime import date
    current_month_start = date.today().replace(day=15).strftime('%Y-%m-%d')

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT 
                dh.user_id, di.title, di.description, dh.deadline_date
            FROM date_history dh
            JOIN date_ideas di ON dh.date_idea_id = di.id
            WHERE dh.month_start_date = ?
            ORDER BY dh.id DESC LIMIT 1
        """, (current_month_start,))
        return await cursor.fetchone()
async def get_all_paired_users():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT DISTINCT id FROM users WHERE partner_id IS NOT NULL")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def save_important_date(user_id, partner_id, title, event_date, reminder_days):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO important_dates (user_id, partner_id, title, event_date, reminder_days) VALUES (?, ?, ?, ?, ?)",
            (user_id, partner_id, title, event_date, reminder_days)
        )
        await db.commit()

async def get_dates_for_reminder():
    from datetime import date, timedelta


    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT user_id, partner_id, title, event_date, reminder_days
            FROM important_dates
            WHERE reminded_at IS NULL OR reminded_at < date('now') 
        """)
        return await cursor.fetchall()

async def mark_date_reminded(user_id, title):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE important_dates SET reminded_at = date('now') WHERE user_id = ? AND title = ?",
            (user_id, title)
        )
        await db.commit()

async def get_all_important_dates(user_id, partner_id):

    async with aiosqlite.connect(DB_NAME) as db:
        # Ищем записи, где user_id является инициатором, ИЛИ partner_id является инициатором
        cursor = await db.execute("""
            SELECT id, title, event_date, reminder_days
            FROM important_dates
            WHERE user_id = ? OR partner_id = ?
            ORDER BY event_date ASC
        """, (user_id, partner_id))
        return await cursor.fetchall()

async def delete_important_date(date_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM important_dates WHERE id = ? AND user_id = ?",
            (date_id, user_id)
        )
        await db.commit()