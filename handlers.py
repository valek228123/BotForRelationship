from email import message
from aiogram import types
from aiogram.filters import Command
from keyboards import (main_menu, wishlist_menu,
                       keyboard,date_menu, important_date_menu)
from database import (save_wishlist, get_partner_id, get_wishlist, save_pair,
                      delete_wishlist_item, save_surprise,save_date_idea,get_all_unused_date_ideas,
                      mark_date_idea_used,get_last_date_sender,save_date_history,get_current_month_date_info,
                       mark_date_reminded,get_dates_for_reminder,save_important_date,
                      get_all_paired_users, get_all_important_dates, delete_important_date)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import random
import re
from datetime import date, timedelta, datetime


user_states = {}
STATE_AWAITING_SURPRISE_TEXT = "awaiting_surprise_text"
STATE_AWAITING_SURPRISE_DELAY = "awaiting_surprise_delay"
STATE_AWAITING_DATE_TITLE = "awaiting_date_title"
STATE_AWAITING_DATE_DESCRIPTION = "awaiting_date_description"
STATE_AWAITING_IMPORTANT_TITLE = "awaiting_important_title"
STATE_AWAITING_IMPORTANT_DATE = "awaiting_important_date"
STATE_AWAITING_IMPORTANT_REMINDER = "awaiting_important_reminder"


async def start_handler(message: types.Message):
   await message.answer("Привет! Я романтичный бот 💌", reply_markup=main_menu)
   await message.answer("Различные команды есть прямо под строкой ввода 😀\n"
                        "Команда /pair нужна для того что бы связать себя со своим партнером,после этой окманды напиши id партнера \n"
                        "Команда /myid покажет твой id",reply_markup=keyboard)


async def unexpected_surprise_handler(callback: types.CallbackQuery):
    partner_id = await get_partner_id(callback.from_user.id)
    if not partner_id:
        await callback.message.answer("Ты ещё не связал аккаунт с партнёром. Используй /pair ID")
        return


    user_states[callback.from_user.id] = STATE_AWAITING_SURPRISE_TEXT
    await callback.message.answer(
        "Напиши сообщение для партнёра, которое он получит позже (например: 'Подари мне цветочки').",
    )



async def send_surprise_later(bot_instance,requester_id, partner_id, text, delay_seconds):
    await asyncio.sleep(delay_seconds)
    try:
        user_object = (await bot_instance.get_chat_member(requester_id, requester_id)).user
        requester_mention = f"[{user_object.first_name}](tg://user?id={user_object.id})"

        await bot_instance.send_message(
            partner_id,
            f"🎁 Неожиданный сюрприз! 🎁\n\n"
            f"Твоя вторая половинка {requester_mention} отправила(а) это сообщение:\n"
            f"«{text}»\n\n"
            f"Это сообщение было отложено, чтобы сохранить элемент неожиданности 😉"
        )
    except Exception as e:
        print(f"Ошибка при отправке сюрприза: {e}")


async def wishlist_handler(callback: types.CallbackQuery):
    await callback.message.answer("Выбери действие:", reply_markup=wishlist_menu)

# Добавление желания
async def add_wishlist_handler(callback: types.CallbackQuery):
    user_states[callback.from_user.id] = "awaiting_wishlist"
    await callback.message.answer("Напиши своё желание. Можно прикрепить фото или просто текст.")


async def this_months_date_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    date_info = await get_current_month_date_info()

    if not date_info:
        await callback.message.answer(
            "Свидание на этот месяц еще не назначено (бот назначает его 15 числа). "
            "Жди уведомления!",

        )
        await callback.message.answer("Выбери действие:", reply_markup=date_menu)
        return

    sender_id, title, description, deadline_date = date_info


    deadline = date.fromisoformat(deadline_date)
    deadline_str = deadline.strftime("%d.%m.%Y")

    if user_id == sender_id:
        await callback.message.answer(
            f"📅 **Свидание месяца: {title}** 📅\n\n"
            f"**Задача:** Организовать это свидание до **{deadline_str}**.\n\n"
            f"**Описание:** {description}\n\n"
            f"Действуй! Время пошло 😉",
            parse_mode="Markdown",
            reply_markup=date_menu
        )
    else:
        await callback.message.answer(
            "💖 **Жди прекрасного времяпровождения** 💖\n\n"
            "Твой партнер уже что-то готовит для тебя... "
            f"Свидание должно состояться до **{deadline_str}**!",
            parse_mode="Markdown",
            reply_markup=date_menu
        )

last_run_check = {}


async def schedule_monthly_date_check(bot_instance):
    last_execution_month = None

    while True:
        now = datetime.now()
        current_month = (now.year, now.month)

        if now.day == 15 and now.hour == 10 and now.minute == 0:
            if last_execution_month != current_month:
                print(f"✅ {now.strftime('%d.%m.%Y %H:%M')} - Назначаем свидание месяца!")
                await assign_monthly_date(bot_instance)
                last_execution_month = current_month

        await asyncio.sleep(60)


async def assign_monthly_date(bot_instance):
    """
    Назначает случайную идею свидания одному из партнеров 15-го числа каждого месяца.
    Организатор чередуется между партнерами.
    """


    if await get_current_month_date_info():
        return

    last_sender_id = await get_last_date_sender()
    all_paired_users = await get_all_paired_users()

    if not all_paired_users:
        print("Ошибка назначения свидания: В базе данных нет связанных пар.")
        return

    current_sender_id = None
    partner_id = None

    if not last_sender_id:
        current_sender_id = all_paired_users[0]
        partner_id = await get_partner_id(current_sender_id)

    else:
        current_sender_id = await get_partner_id(last_sender_id)
        partner_id = last_sender_id

        if not current_sender_id:
            current_sender_id = all_paired_users[0]
            partner_id = await get_partner_id(current_sender_id)


    if not current_sender_id or not partner_id:
        print(
            f"Ошибка назначения свидания: Не удалось найти полную пару для чередования (current_sender_id: {current_sender_id}, partner_id: {partner_id}).")
        return

    ideas = await get_all_unused_date_ideas()
    if not ideas:
        await bot_instance.send_message(current_sender_id, "Нет доступных идей для свиданий! Пожалуйста, добавьте их.")
        return

    random_idea = random.choice(ideas[:5])
    idea_id, title, description = random_idea


    month_start_date = date.today().replace(day=15)
    deadline_date = month_start_date + timedelta(days=30)

    await save_date_history(
        current_sender_id,
        idea_id,
        month_start_date.strftime('%Y-%m-%d'),
        deadline_date.strftime('%Y-%m-%d')
    )
    await mark_date_idea_used(idea_id)


    await bot_instance.send_message(
        current_sender_id,
        f"🎉 Свидание месяца назначено! 🎉\n\n"
        f"Задача месяца (для тебя): Организовать свидание:\n"
        f"Название: {title}\n"
        f"Описание: {description}\n\n"
        f"Срок выполнения: До {deadline_date.strftime('%d.%m.%Y')}. Нажми кнопку 'This Month's Date 📅' для напоминания!",
        parse_mode="Markdown"
    )


    await bot_instance.send_message(
        partner_id,
        "🤫 **Секрет!** Твой партнер только что получил задание на Свидание Месяца. Жди сюрприза!",
        parse_mode="Markdown"
    )
async def add_date_idea_handler(callback: types.CallbackQuery):
    user_states[callback.from_user.id] = STATE_AWAITING_DATE_TITLE
    await callback.message.answer("Введите **название** идеи свидания (например: 'Романтический ужин на крыше').", parse_mode="Markdown")



async def message_handler(message: types.Message):
    state = user_states.get(message.from_user.id)
    user_id = message.from_user.id
    if state == "awaiting_wishlist":
        text = message.caption if message.photo else message.text
        photo_id = message.photo[-1].file_id if message.photo else None
        await save_wishlist(message.from_user.id, text, photo_id)

        await message.answer("Желание добавлено 💫")
        await asyncio.sleep(3)
        user_states.pop(message.from_user.id, None)
        await message.answer("Выбери действие:", reply_markup=wishlist_menu)
    elif state == STATE_AWAITING_SURPRISE_TEXT:
        surprise_text = message.text
        user_states[user_id] = {
            "state": STATE_AWAITING_SURPRISE_DELAY,
            "text": surprise_text
        }
        await message.answer(
            "Отлично! Теперь укажи рамки времени, в течение которых я должен отправить этот сюрприз. "
            "Используй формат: от X до Y дней (или часов, или месяцев). \n\n"
            "*Пример: от 1 до 5 дней*",
             parse_mode = "Markdown"
        )
        return


    elif state and isinstance(state, dict) and state.get("state") == STATE_AWAITING_SURPRISE_DELAY:

        surprise_text = state["text"]
        partner_id = await get_partner_id(user_id)

        if not partner_id:
            await message.answer(
                "Ошибка: не удалось найти ID партнера. Убедитесь, что вы связали аккаунты с помощью /pair ID.",parse_mode="Markdown")
            user_states.pop(user_id, None)
            return

        match = re.search(
            r'от\s*(\d+)\s*до\s*(\d+)\s*(дней|дня|день|часов|часа|час|месяцев|месяца|месяц)',
            message.text,
            re.IGNORECASE
        )

        if not match:
            await message.answer(
                "Не удалось распознать формат. Пожалуйста, используй формат: от X до Y дней (или часов, или месяцев).",
            )
            return

        min_amount = int(match.group(1))
        max_amount = int(match.group(2))
        unit = match.group(3).lower()


        if unit in ('час', 'часа', 'часов'):
            SEC_MULTIPLIER = 3600
        elif unit in ('день', 'дня', 'дней'):
            SEC_MULTIPLIER = 86400
        elif unit in ('месяц', 'месяца', 'месяцев'):
            SEC_MULTIPLIER = 30 * 86400
        else:
            await message.answer("Неизвестная единица времени. Используйте: дни, часы, месяцы.")
            return


        min_delay_seconds = min_amount * SEC_MULTIPLIER
        max_delay_seconds = max_amount * SEC_MULTIPLIER

        if min_delay_seconds >= max_delay_seconds:
            await message.answer("Минимальный срок должен быть меньше максимального.")
            return

        delay_seconds = random.randint(min_delay_seconds, max_delay_seconds)

        await save_surprise(user_id, partner_id, surprise_text, delay_seconds)
        asyncio.create_task(send_surprise_later(message.bot,user_id, partner_id, surprise_text, delay_seconds))

        user_states.pop(user_id, None)

        delay_all = 0
        delay_unit_text = unit

        if unit in ('час', 'часа', 'часов'):
            delay_all = round(delay_seconds / 3600)
            delay_unit_text = "часов"
        elif unit in ('день', 'дня', 'дней'):
            delay_all = round(delay_seconds / 86400)
            delay_unit_text = "дней"
        elif unit in ('месяц', 'месяца', 'месяцев'):
            delay_all = round(delay_seconds / (30 * 86400))
            delay_unit_text = "месяцев"

        await message.answer(
            f"Сообщение о сюрпризе принято! Я отправлю его партнёру в случайный момент. ",
            parse_mode="Markdown"
        )
        await message.answer("Выбери действие:", reply_markup=main_menu)
        return
    elif state == STATE_AWAITING_DATE_TITLE:
        user_states[user_id] = {
            "state": STATE_AWAITING_DATE_DESCRIPTION,
            "title": message.text
        }
        await message.answer("Теперь введите **подробное описание** свидания (один абзац).", parse_mode="Markdown")
        return

    elif state and isinstance(state, dict) and state.get("state") == STATE_AWAITING_DATE_DESCRIPTION:
        title = state["title"]
        description = message.text

        await save_date_idea(title, description)

        user_states.pop(user_id, None)
        await message.answer(
            f"Идея свидания '{title}' успешно добавлена!",
            parse_mode="Markdown",
        )
        await message.answer("Выбери действие:", reply_markup=date_menu)
        return
    if state == STATE_AWAITING_IMPORTANT_TITLE:
        user_states[user_id] = {
            "state": STATE_AWAITING_IMPORTANT_DATE,
            "title": message.text
        }
        await message.answer(
            "Отлично! Теперь введите саму дату события (в формате ГГГГ-ММ-ДД, например: 2026-06-25):",
            parse_mode="Markdown")
        return

    elif state and isinstance(state, dict) and state.get("state") == STATE_AWAITING_IMPORTANT_DATE:
        try:
            event_date = datetime.strptime(message.text, '%Y-%m-%d').date()

            user_states[user_id].update({
                "state": STATE_AWAITING_IMPORTANT_REMINDER,
                "event_date": event_date.strftime('%Y-%m-%d')
            })

            await message.answer(
                "Дата сохранена! За сколько **дней** до события мне нужно напомнить? (Введите число, например: 7):")
        except ValueError:
            await message.answer("Неверный формат даты. Используйте ГГГГ-ММ-ДД (например: 2026-06-25).")
        return

    elif state and isinstance(state, dict) and state.get("state") == STATE_AWAITING_IMPORTANT_REMINDER:
        try:
            reminder_days = int(message.text)

            title = user_states[user_id]["title"]
            event_date_str = user_states[user_id]["event_date"]
            partner_id = await get_partner_id(user_id)

            await save_important_date(user_id, partner_id, title, event_date_str, reminder_days)

            user_states.pop(user_id, None)
            await message.answer(
                f"Важная дата **'{title}'** ({event_date_str}) сохранена!\n"
                f"Напомню за **{reminder_days}** дней до события. ✨",
                parse_mode="Markdown"
            )
            await message.answer("Выбери действие:", reply_markup=important_date_menu)
        except ValueError:
            await message.answer("Неверный формат. Пожалуйста, введите число дней (например: 7).")
        return
    if state is None:
        await message.answer("Выбери действие:", reply_markup=main_menu)
        return


async def back_to_menu_handler(callback: types.CallbackQuery):
    await callback.message.answer("Меню :)\nВыбирай действие:", reply_markup=main_menu)



async def view_partner_handler(callback: types.CallbackQuery):
    partner_id = await get_partner_id(callback.from_user.id)
    if not partner_id:
        await callback.message.answer("Ты ещё не связал аккаунт с партнёром. Используй /pair ID")
        return
    wishes = await get_wishlist(partner_id)
    if not wishes:
        await callback.message.answer("У партнёра пока нет желаний 💤")
    else:
        for _, text, photo_id in wishes:
            if photo_id:
                await callback.message.answer_photo(photo_id, caption=text)
            else:
                await callback.message.answer(f"💭 {text}")
    await callback.message.answer("Выбери действие:", reply_markup=wishlist_menu)
async def view_my_handler(callback: types.CallbackQuery):
    my_id =  callback.from_user.id
    wishes = await get_wishlist(my_id)
    if not wishes:
        await callback.message.answer("У тебя пока нет желаний 💤")
    else:
        for _, text, photo_id in wishes:
            if photo_id:
                await callback.message.answer_photo(photo_id, caption=text)
            else:
                await callback.message.answer(f"💭 {text}")
    await callback.message.answer("Выбери действие:", reply_markup=wishlist_menu)
async def pair_handler(message: types.Message):
    try:
        partner_id = int(message.text.split()[1])
        await save_pair(message.from_user.id, partner_id)
        await message.answer("Вы теперь связаны как пара 💞")
    except:
        await message.answer("Используй формат: /pair ID")
    await message.answer("Выбери действие:", reply_markup=wishlist_menu)

async def delete_wishlist_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    wishes = await get_wishlist(user_id)
    if not wishes:
        await callback.message.answer("У тебя пока нет желаний для удаления 💤")
        return

    buttons = []
    for wish_id, text, photo_id in wishes:
        button_text = text if text else "Фото"
        buttons.append([InlineKeyboardButton(
            text=f"❌ {button_text[:20]}...",
            callback_data=f"del_{wish_id}"
        )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer("Выбери желание для удаления:", reply_markup=keyboard)

async def confirm_delete(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    item_id = int(callback.data.split("_")[1])
    await delete_wishlist_item(item_id, user_id)
    await callback.message.answer("Желание удалено ❌")
    await callback.message.answer("Выбери действие:", reply_markup=wishlist_menu)

async def my_id_handler(message: types.Message):
    await message.answer(f"Твой ID: {message.from_user.id}")


async def important_date_menu_handler(callback: types.CallbackQuery):
    await callback.message.answer("Меню Важных Дат:", reply_markup=important_date_menu)

# 1. Начало добавления даты
async def add_important_date_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    partner_id = await get_partner_id(user_id)
    if not partner_id:
        await callback.message.answer("Ты еще не в паре! Используй команду /pair ID")
        return

    user_states[user_id] = STATE_AWAITING_IMPORTANT_TITLE
    await callback.message.answer("Введите **название** важной даты (например: 'Годовщина встречи'):", parse_mode='Markdown')


# 3. Ежедневный планировщик напоминаний
async def daily_reminder_check(bot_instance):
    """Ежедневно проверяет, нужно ли отправлять напоминания о важных датах."""
    while True:
        now = datetime.now()
        if now.hour == 10 and now.minute == 0:

            print("--- Запуск ежедневной проверки напоминаний ---")

            reminders = await get_dates_for_reminder()
            today = date.today()

            for user_id, partner_id, title, event_date_str, reminder_days in reminders:

                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()

                reminder_date = event_date - timedelta(days=reminder_days)

                if today >= reminder_date:
                    days_left = (event_date - today).days

                    text = (
                        f"🔔 **Напоминание о важной дате!** 🔔\n\n"
                        f"**Повод:** {title}\n"
                        f"**Событие:** {event_date.strftime('%d.%m.%Y')}\n"
                        f"**Осталось:** **{days_left}** дней!\n\n"
                        f"Пора планировать сюрприз! 😉"
                    )
                    try:
                        # Отправляем обоим: инициатору и партнеру (если не хочет сам)
                        await bot_instance.send_message(user_id, text, parse_mode='Markdown')
                        await bot_instance.send_message(partner_id, text, parse_mode='Markdown')

                        await mark_date_reminded(user_id, title)
                    except Exception as e:
                        print(f"Ошибка отправки напоминания пользователю {user_id}: {e}")

        await asyncio.sleep(60)


async def view_all_important_dates_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    partner_id = await get_partner_id(user_id)

    if not partner_id:
        await callback.message.answer("Ты еще не в паре! Используй команду /pair ID")
        return

    dates = await get_all_important_dates(user_id, partner_id)

    if not dates:
        await callback.message.answer("У вас пока нет сохраненных важных дат! Добавьте первую 💖",
                                      reply_markup=important_date_menu)
        return

    text = "🗓️ **Ваши общие важные даты:**\n\n"

    today = date.today()

    for date_id, title, event_date_str, reminder_days in dates:
        event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
        days_left = (event_date - today).days

        if days_left < 0:
            status = f"✅ Прошло {-days_left} дн."
        elif days_left == 0:
            status = "🚨 **СЕГОДНЯ!**"
        else:
            status = f"⏱️ Через {days_left} дн."

        text += (
            f"**{title}**\n"
            f"Дата: {event_date.strftime('%d.%m.%Y')} ({status})\n"
            f"Напомнить: за {reminder_days} дней.\n"
            f"---\n"
        )

    await callback.message.answer(text, parse_mode='Markdown', reply_markup=important_date_menu)


async def delete_important_date_handler(callback: types.CallbackQuery):
    """Запрашивает подтверждение удаления важной даты."""
    user_id = callback.from_user.id
    partner_id = await get_partner_id(user_id)


    dates = await get_all_important_dates(user_id, partner_id)

    my_dates = [d for d in dates if d[0] is not None]

    if not my_dates:
        await callback.message.answer("Ты не создавал никаких важных дат для удаления 💤",
                                      reply_markup=important_date_menu)
        return

    buttons = []
    for date_id, title, _, _ in my_dates:
        buttons.append([InlineKeyboardButton(
            text=f"❌ {title}",
            callback_data=f"del_date_{date_id}"
        )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer("Выбери дату, которую хочешь удалить (ты можешь удалять только СВОИ даты):",
                                  reply_markup=keyboard)


async def confirm_delete_important_date(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    try:
        date_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка в данных для удаления.", show_alert=True)
        return

    await delete_important_date(date_id, user_id)
    await callback.message.answer("Важная дата удалена ❌", reply_markup=important_date_menu)