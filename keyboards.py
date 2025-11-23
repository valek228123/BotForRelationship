from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton,  ReplyKeyboardMarkup, KeyboardButton

main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="WishList 💭", callback_data="wishlist")],
    [InlineKeyboardButton(text="Unexpected Surprise 🎁", callback_data="unexpected_surprise")],
    [InlineKeyboardButton(text="This Month's Date 📅", callback_data="this_months_date")],
    [InlineKeyboardButton(text="An Important Date ✨", callback_data="important_date")],
])
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/Назад в меню ⬅️"), KeyboardButton(text="/myid")],

    ],
    resize_keyboard=True,  # Подгоняет размер кнопок
)

wishlist_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Добавить в свой WL", callback_data="add_wishlist")],
    [InlineKeyboardButton(text="👀 Посмотреть WL партнёра", callback_data="view_partner_wishlist")],
    [InlineKeyboardButton(text="👀 Посмотреть свой WL", callback_data="view_my_wishlist")],
    [InlineKeyboardButton(text="❌ Удалить желание", callback_data="delete_wishlist")],
    [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]

])
date_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Добавить идею свидания", callback_data="add_date_idea")],
    [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
])

important_date_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Добавить дату", callback_data="add_important_date")],
    [InlineKeyboardButton(text="👀 Посмотреть ВСЕ даты", callback_data="view_all_important_dates")],
    [InlineKeyboardButton(text="❌ Удалить дату", callback_data="delete_important_date")],
    [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
])
