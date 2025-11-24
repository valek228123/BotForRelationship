import asyncio
import os
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import CallbackQuery
from aiogram.filters import Command
from config import BOT_TOKEN
from handlers import (start_handler, my_id_handler, wishlist_handler, add_wishlist_handler,
                      view_partner_handler, view_my_handler, pair_handler, delete_wishlist_handler,
                      back_to_menu_handler, confirm_delete, message_handler,
                      unexpected_surprise_handler, this_months_date_handler,
                      add_date_idea_handler, daily_reminder_check, important_date_menu_handler,
                      add_important_date_handler, delete_important_date_handler,
                      view_all_important_dates_handler, confirm_delete_important_date)
from database import init_db
from handlers import schedule_monthly_date_check
from datetime import datetime

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ВСЕ ТВОИ ОБРАБОТЧИКИ (оставь как были)
@dp.message(Command("start"))
async def start(message: types.Message):
    await start_handler(message)


@dp.message(Command("myid"))
async def myid(message: types.Message):
    await my_id_handler(message)


@dp.message(Command("pair"))
async def pair(message: types.Message):
    await pair_handler(message)


@dp.callback_query(lambda c: c.data == "wishlist")
async def wishlist(callback: CallbackQuery):
    await wishlist_handler(callback)


@dp.callback_query(lambda c: c.data == "add_wishlist")
async def add_wishlist(callback: CallbackQuery):
    await add_wishlist_handler(callback)


@dp.callback_query(lambda c: c.data == "view_partner_wishlist")
async def view_partner(callback: CallbackQuery):
    await view_partner_handler(callback)


@dp.callback_query(lambda c: c.data == "view_my_wishlist")
async def view_my_wishlist(callback: CallbackQuery):
    await view_my_handler(callback)


@dp.callback_query(lambda c: c.data == "delete_wishlist")
async def delete_wishlist(callback: CallbackQuery):
    await delete_wishlist_handler(callback)


@dp.callback_query(lambda c: c.data.startswith("del_") and not c.data.startswith("del_date_"))
async def confirm_delete_handler(callback: CallbackQuery):
    await confirm_delete(callback)


@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await back_to_menu_handler(callback)


@dp.callback_query(lambda c: c.data == "unexpected_surprise")
async def unexpected_surprise(callback: CallbackQuery):
    await unexpected_surprise_handler(callback)


@dp.callback_query(lambda c: c.data == "this_months_date")
async def this_months_date(callback: CallbackQuery):
    await this_months_date_handler(callback)


@dp.callback_query(lambda c: c.data == "add_date_idea")
async def add_date_idea(callback: CallbackQuery):
    await add_date_idea_handler(callback)


@dp.callback_query(lambda c: c.data == "important_date")
async def important_date_menu(callback: CallbackQuery):
    await important_date_menu_handler(callback)


@dp.callback_query(lambda c: c.data == "add_important_date")
async def add_important_date(callback: CallbackQuery):
    await add_important_date_handler(callback)


@dp.callback_query(lambda c: c.data == "view_all_important_dates")
async def view_all_important_dates(callback: CallbackQuery):
    await view_all_important_dates_handler(callback)


@dp.callback_query(lambda c: c.data == "delete_important_date")
async def delete_important_date(callback: CallbackQuery):
    await delete_important_date_handler(callback)


@dp.callback_query(lambda c: c.data.startswith("del_date_"))
async def confirm_delete_date_handler(callback: CallbackQuery):
    await confirm_delete_important_date(callback)


@dp.message()
async def handle_message(message: types.Message):
    await message_handler(message)


async def keep_app_awake():
    """Периодически 'будит' приложение запросами"""
    app_url = os.getenv("RENDER_EXTERNAL_URL", "https://your-app-name.onrender.com")

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{app_url}/health") as resp:
                    print(f"🔔 [{datetime.now()}] Приложение разбужено. Статус: {resp.status}")
        except Exception as e:
            print(f"❌ Ошибка пробуждения: {e}")

        await asyncio.sleep(480)


async def main():
    await bot.delete_webhook()
    print("✅ Webhook удален, переходим в режим polling")

    await init_db()
    print("🗄️ База данных инициализирована")

    asyncio.create_task(schedule_monthly_date_check(bot))
    asyncio.create_task(daily_reminder_check(bot))
    print("📅 Планировщики запущены")

    asyncio.create_task(keep_app_awake())
    print("🔔 Авто-пробуждение запущено")

    app = web.Application()

    async def health_check(request):
        return web.Response(text="🤖 Бот работает! 💕")

    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    print(f"🌐 Health сервер запущен на порту {port}")
    print("🤖 Бот запускается в режиме polling...")


    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())