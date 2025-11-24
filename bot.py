import asyncio
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


# ==============================================
# ФУНКЦИЯ "БУДИЛЬНИКА" - НЕ ДАЁТ БОТУ УСНУТЬ
# ==============================================

async def keep_bot_awake():
    """
    Эта функция каждые 10 минут проверяет, что бот живой.
    Она просто делает маленький запрос к Telegram API.
    Это не даст Render усыпить нашего бота!
    """
    while True:
        try:
            user = await bot.get_me()
            print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Будильник сработал! Бот жив, имя: {user.first_name}")
        except Exception as e:
            print(f"⚠️ Ошибка в будильнике: {e}")

        # Ждём 10 минут (600 секунд) до следующей проверки
        await asyncio.sleep(600)


# ==============================================
# ВАШИ СУЩЕСТВУЮЩИЕ ХЭНДЛЕРЫ (НИЧЕГО НЕ МЕНЯЕМ)
# ==============================================

@dp.message(Command("start"))
async def start(message: types.Message):
    await start_handler(message)


@dp.message(Command("myid"))
async def myid(message: types.Message):
    await my_id_handler(message)


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
async def view_partner(callback: CallbackQuery):
    await view_my_handler(callback)


@dp.message(Command("pair"))
async def pair(message: types.Message):
    await pair_handler(message)


@dp.callback_query(lambda c: c.data == "delete_wishlist")
async def delete_wishlist(callback: CallbackQuery):
    await delete_wishlist_handler(callback)


@dp.callback_query(lambda c: c.data.startswith("del_") and not c.data.startswith("del_date_"))
async def confirm_delete_handler(callback: CallbackQuery):
    await confirm_delete(callback)


@dp.callback_query(lambda c: c.data.startswith("back_to_menu"))
async def back_to_menu(callback: CallbackQuery):
    await back_to_menu_handler(callback)


@dp.message()
async def handle_message(message: types.Message):
    await message_handler(message)


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


# ==============================================
# ОСНОВНАЯ ФУНКЦИЯ ЗАПУСКА
# ==============================================

async def main():
    await init_db()
    print("База данных инициализирована.")

    # ==============================================
    # ЗАПУСКАЕМ БУДИЛЬНИК - ВАЖНАЯ СТРОЧКА!
    # ==============================================
    asyncio.create_task(keep_bot_awake())
    print("🔄 Будильник запущен - бот не уснёт!")

    print("Планировщик ежемесячного свидания запущен.")
    asyncio.create_task(schedule_monthly_date_check(bot))
    print("Планировщик ежедневных напоминаний запущен.")
    asyncio.create_task(daily_reminder_check(bot))

    print("🤖 Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())