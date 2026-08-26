import asyncio
import os
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from google import genai

BOT_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

CHANNEL_USERNAME = "@alphamasss"
ADMIN_ID = 7847949636
SUPPORT_USERNAME = "@Alphamash"

bot = Bot(token=BOT_TOKEN)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
dp = Dispatcher(storage=MemoryStorage())

USERS_FILE = "users.txt"
REVIEWS_FILE = "reviews.txt"
REFERRALS_FILE = "referrals.txt"
PURCHASES_FILE = "purchases.txt"

USER_BALANCES = {}
USER_PHOTOS = {}

PRODUKTIB = {
    'сухой': {'title': 'Сушка', 'цена': 49, 'тип': 'channel'},
    'масса': {'title': 'Массонабор', 'цена': 49, 'тип': 'channel'},
    'rost': {'title': 'Альфа-Рост', 'цена': 99, 'тип': 'channel'},
    'rustam': {'title': 'Методика Р. Ахметова', 'цена': 99, 'тип': 'channel'},
    'сертори': {'title': 'Методика Сертори', 'цена': 99, 'тип': 'channel'},
    'pers_30': {'title': 'Программа 30 дней', 'цена': 149, 'тип': 'personal_30'},
    'pers_year': {'title': 'Программа на год', 'цена': 499, 'тип': 'personal_year'},
    'eval_1': {'title': '1 оценка формы', 'цена': 3, 'тип': 'eval', 'count': 1},
    'eval_5': {'title': '5 оценок формы', 'цена': 15, 'тип': 'eval', 'count': 5},
    'eval_10': {'title': '10 оценок формы', 'цена': 30, 'тип': 'eval', 'count': 10},
    'eval_30': {'title': '30 оценок формы', 'цена': 90, 'тип': 'eval', 'count': 30},
    'eval_50': {'title': '50 оценок формы', 'цена': 150, 'тип': 'eval', 'count': 50},
    'eval_100': {'title': '100 оценок формы', 'цена': 300, 'тип': 'eval', 'count': 100},
}

class ProgramStates(StatesGroup):
    prog_type = State()
    goal = State()
    age = State()
    height = State()
    weight = State()
    experience = State()
    conditions = State()
    injuries = State()
    supplements = State()

class FormStates(StatesGroup):
    waiting_for_photos = State()

class BroadcastState(StatesGroup):
    waiting_for_message = State()

class ReviewState(StatesGroup):
    waiting_for_review_text = State()

class AddBalanceState(StatesGroup):
    waiting_for_data = State()

def add_user(user_id: int):
    users = set()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().isdigit():
                    users.add(int(line.strip()))
    if user_id not in users:
        with open(USERS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{user_id}\n")

def get_all_users() -> list:
    users = []
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().isdigit():
                    users.append(int(line.strip()))
    return users

def record_purchase(user_id: int):
    purchases = set()
    if os.path.exists(PURCHASES_FILE):
        with open(PURCHASES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().isdigit():
                    purchases.add(int(line.strip()))
    purchases.add(user_id)
    with open(PURCHASES_FILE, "w", encoding="utf-8") as f:
        for uid in purchases:
            f.write(f"{uid}\n")

def has_user_purchased(user_id: int) -> bool:
    if not os.path.exists(PURCHASES_FILE):
        return False
    with open(PURCHASES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().isdigit() and int(line.strip()) == user_id:
                return True
    return False

def save_review(user_name: str, text: str):
    with open(REVIEWS_FILE, "a", encoding="utf-8") as f:
        f.write(f"@{user_name}: {text}\n")

def get_reviews_list() -> list:
    if not os.path.exists(REVIEWS_FILE):
        return []
    with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    return lines

def delete_review_by_index(index: int):
    reviews = get_reviews_list()
    if 0 <= index < len(reviews):
        reviews.pop(index)
        with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
            for rev in reviews:
                f.write(f"{rev}\n")

def save_referral_link(new_user_id: int, referrer_id: int):
    if get_referrer(new_user_id) is None and new_user_id != referrer_id:
        with open(REFERRALS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{new_user_id}:{referrer_id}\n")

def get_referrer(new_user_id: int):
    if not os.path.exists(REFERRALS_FILE):
        return None
    with open(REFERRALS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                parts = line.strip().split(":")
                if parts[0].isdigit() and int(parts[0]) == new_user_id:
                    return int(parts[1])
    return None

def mark_referral_rewarded(new_user_id: int):
    if not os.path.exists(REFERRALS_FILE):
        return
    lines = []
    with open(REFERRALS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(REFERRALS_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            if ":" in line:
                parts = line.strip().split(":")
                if parts[0].isdigit() and int(parts[0]) == new_user_id:
                    if len(parts) == 2:
                        f.write(f"{parts[0]}:{parts[1]}:rewarded\n")
                        continue
            f.write(line)

def is_referral_rewarded(new_user_id: int) -> bool:
    if not os.path.exists(REFERRALS_FILE):
        return False
    with open(REFERRALS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                parts = line.strip().split(":")
                if parts[0].isdigit() and int(parts[0]) == new_user_id:
                    if len(parts) >= 3 and parts[2] == "rewarded":
                        return True
    return False

def get_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/alphamasss")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
    ])

def main_menu():
    kb = [
        [KeyboardButton(text="📊 Оценка формы по фото"), KeyboardButton(text="👤 Баланс")],
        [KeyboardButton(text="🏋️ 🧬 Базовые протоколы"), KeyboardButton(text="🔥 Персональные программы")],
        [KeyboardButton(text="💎 Купить оценки / Магазин"), KeyboardButton(text="👥 Реферальная система")],
        [KeyboardButton(text="💬 Отзывы"), KeyboardButton(text="🛠 Поддержка")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📈 Статистика бота", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📁 Выгрузить базу ID (txt)", callback_data="admin_export_users")],
        [InlineKeyboardButton(text="🎁 Выдать баланс юзеру", callback_data="admin_add_balance")],
        [InlineKeyboardButton(text="🗑 Управлять / удалить отзывы", callback_data="admin_manage_reviews")],
        [InlineKeyboardButton(text="🔙 Закрыть панель", callback_data="back_main")]
    ])

def basic_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🧬 Сушка – 49 ⭐', callback_data='buy_сухой')],
        [InlineKeyboardButton(text='🔥 Массонабор – 49 ⭐', callback_data='buy_масса')],
        [InlineKeyboardButton(text='📈 Альфа-Рост – 99 ⭐', callback_data='buy_rost')],
        [InlineKeyboardButton(text='📜 Методика Р. Ахметова – 99 ⭐', callback_data='buy_rustam')],
        [InlineKeyboardButton(text='⚡ Методика Сертори – 99 ⭐', callback_data='buy_сертори')],
        [InlineKeyboardButton(text='🔙 Назад в меню', callback_data='back_main')],
    ])

def personal_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎯 Программа 30 дней – 149 ⭐', callback_data='buy_pers_30')],
        [InlineKeyboardButton(text='👑 Программа на год – 499 ⭐', callback_data='buy_pers_year')],
        [InlineKeyboardButton(text='🔙 Назад в меню', callback_data='back_main')],
    ])

def shop_eval_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='1 оценка – 3 ⭐', callback_data='buy_eval_1')],
        [InlineKeyboardButton(text='5 оценок – 15 ⭐', callback_data='buy_eval_5')],
        [InlineKeyboardButton(text='10 оценок – 30 ⭐', callback_data='buy_eval_10')],
        [InlineKeyboardButton(text='30 оценок – 90 ⭐', callback_data='buy_eval_30')],
        [InlineKeyboardButton(text='50 оценок – 150 ⭐', callback_data='buy_eval_50')],
        [InlineKeyboardButton(text='100 оценок – 300 ⭐', callback_data='buy_eval_100')],
        [InlineKeyboardButton(text='🔙 Назад в меню', callback_data='back_main')]
    ])

app = Flask('')

@app.route('/')
def home():
    return 'ALPHA MASS Bot is active!'

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return False
@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    add_user(user_id)
    
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref"):
        try:
            referrer_id = int(args[1].replace("ref", ""))
            save_referral_link(user_id, referrer_id)
        except ValueError:
            pass

    if not await check_subscription(user_id):
        await message.answer(
            "⚡ <b>АЛЬФА-МАССА</b>\n\nДля доступа к боту и получения бонусов подпишитесь на канал:", 
            reply_markup=get_sub_keyboard(), 
            parse_mode='HTML'
        )
        return

    if user_id not in USER_BALANCES:
        USER_BALANCES[user_id] = 5

    referrer_id = get_referrer(user_id)
    if referrer_id and not is_referral_rewarded(user_id):
        mark_referral_rewarded(user_id)
        USER_BALANCES[referrer_id] = USER_BALANCES.get(referrer_id, 5) + 2
        try:
            await bot.send_message(
                referrer_id, 
                "🎉 <b>Реферальный бонус!</b>\nПо вашей ссылке приглашенный друг подписался на канал. Вам зачислено +2 бесплатные оценки формы!", 
                parse_mode='HTML'
            )
        except Exception:
            pass

    await message.answer("⚡ <b>АЛЬФА-МАССА</b>\n\nГлавное меню:", reply_markup=main_menu(), parse_mode='HTML')

@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: CallbackQuery):
    user_id = callback.from_user.id
    add_user(user_id)
    
    if await check_subscription(user_id):
        if user_id not in USER_BALANCES:
            USER_BALANCES[user_id] = 5

        referrer_id = get_referrer(user_id)
        if referrer_id and not is_referral_rewarded(user_id):
            mark_referral_rewarded(user_id)
            USER_BALANCES[referrer_id] = USER_BALANCES.get(referrer_id, 5) + 2
            try:
                await bot.send_message(
                    referrer_id, 
                    "🎉 <b>Реферальный бонус!</b>\nПо вашей ссылке приглашенный друг подписался на канал. Вам зачислено +2 бесплатные оценки формы!", 
                    parse_mode='HTML'
                )
            except Exception:
                pass

        await callback.message.edit_text("✅ Подписка подтверждена!")
        await callback.message.answer("Главное меню:", reply_markup=main_menu(), parse_mode='HTML')
    else:
        await callback.answer("❌ Вы еще не подписались на канал!", show_alert=True)

@dp.message(F.text == "👤 Баланс")
async def balance_menu_msg(message: Message):
    user_id = message.from_user.id
    if user_id not in USER_BALANCES:
        USER_BALANCES[user_id] = 5
    balance = USER_BALANCES.get(user_id, 5)
    
    text = (
        "👤 <b>Ваш личный кабинет</b>\n\n"
        f"💎 Доступно оценок формы: <b>{balance}</b>\n\n"
        "<i>Каждая оценка позволяет загрузить до 5 фотографий вашей формы с разных ракурсов для детального анализа ИИ.</i>"
    )
    await message.answer(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить оценки", callback_data="goto_shop")],
        [InlineKeyboardButton(text="👥 Пригласить друзей (+2 оценки)", callback_data="goto_ref")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_main")]
    ]))

@dp.message(F.text == "🛠 Поддержка")
async def support_menu_msg(message: Message):
    text = (
        "🛠 <b>Служба поддержки ALPHA MASS</b>\n\n"
        f"По всем вопросам, проблемам с оплатой или получением материалов обращайтесь к администратору: <b>{SUPPORT_USERNAME}</b>"
    )
    await message.answer(text, parse_mode='HTML', reply_markup=main_menu())

@dp.callback_query(F.data == "goto_shop")
async def goto_shop_cb(callback: CallbackQuery):
    user_id = callback.from_user.id
    balance = USER_BALANCES.get(user_id, 5)
    await callback.message.edit_text(f"💎 <b>Магазин оценок</b>\n\nВаш текущий баланс: <b>{balance}</b> оценок.", parse_mode='HTML', reply_markup=shop_eval_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "goto_ref")
async def goto_ref_cb(callback: CallbackQuery):
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref{user_id}"
    
    text = (
        "👥 <b>Реферальная программа ALPHA MASS</b>\n\n"
        "Приглашайте друзей в бота и получайте <b>+2 бесплатные оценки формы</b> за каждого приглашенного участника!\n\n"
        f"🔗 <b>Ваша персональная ссылка:</b>\n<code>{ref_link}</code>"
    )
    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_main")]
    ]))
    await callback.answer()

@dp.message(F.text == "👥 Реферальная система")
async def referral_menu_msg(message: Message):
    user_id = message.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref{user_id}"
    
    text = (
        "👥 <b>Реферальная программа ALPHA MASS</b>\n\n"
        "Приглашайте друзей в бота и получайте <b>+2 бесплатные оценки формы</b> за каждого приглашенного участника!\n\n"
        "<i>Награда зачисляется автоматически сразу после того, как ваш друг запустит бота и подпишется на наш канал.</i>\n\n"
        f"🔗 <b>Ваша персональная ссылка:</b>\n<code>{ref_link}</code>"
    )
    await message.answer(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_main")]
    ]))

@dp.message(Command("admin"))
async def admin_panel_cmd(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🔐 <b>Панель администратора</b>", parse_mode='HTML', reply_markup=admin_keyboard())

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещен!", show_alert=True)
        return
    users_count = len(get_all_users())
    await callback.message.edit_text(f"📊 <b>Статистика бота:</b>\n\n👥 Всего пользователей: {users_count}", parse_mode='HTML', reply_markup=admin_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin_export_users")
async def admin_export_users_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещен!", show_alert=True)
        return
    if os.path.exists(USERS_FILE):
        file_bytes = open(USERS_FILE, "rb").read()
        document = BufferedInputFile(file_bytes, filename="users_list.txt")
        await callback.message.answer_document(document, caption="📁 Список всех ID пользователей бота")
    else:
        await callback.answer("Файл пользователей пуст!", show_alert=True)
    await callback.answer()

@dp.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещен!", show_alert=True)
        return
    await state.set_state(AddBalanceState.waiting_for_data)
    await callback.message.edit_text("🎁 Введите через пробел <b>ID пользователя</b> и <b>количество оценок</b> для выдачи:\n\n<i>Пример: 123456789 10</i>", parse_mode='HTML')
    await callback.answer()

@dp.message(AddBalanceState.waiting_for_data)
async def process_add_balance(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    parts = message.text.split()
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        target_uid = int(parts[0])
        amount = int(parts[1])
        USER_BALANCES[target_uid] = USER_BALANCES.get(target_uid, 5) + amount
        await message.answer(f"✅ Пользователю <code>{target_uid}</code> успешно добавлено <b>{amount}</b> оценок!", parse_mode='HTML', reply_markup=admin_keyboard())
        try:
            await bot.send_message(target_uid, f"🎁 Администратор начислил вам <b>{amount}</b> дополнительных оценок формы!", parse_mode='HTML')
        except:
            pass
    else:
        await message.answer("❌ Неверный формат! Попробуйте снова через кнопку в панели.", reply_markup=admin_keyboard())

@dp.callback_query(F.data == "admin_manage_reviews")
async def admin_manage_reviews_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещен!", show_alert=True)
        return
    reviews = get_reviews_list()
    if not reviews:
        await callback.message.edit_text("💬 Отзывов пока нет.", parse_mode='HTML', reply_markup=admin_keyboard())
        await callback.answer()
        return
    
    kb = []
    for idx, rev in enumerate(reviews):
        short_text = rev[:30] + "..." if len(rev) > 30 else rev
        kb.append([InlineKeyboardButton(text=f"❌ Удалить: {short_text}", callback_data=f"del_rev_{idx}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад в админку", callback_data="back_admin")])
    
    await callback.message.edit_text("🗑 <b>Управление отзывами:</b>\nНажмите на кнопку под отзывом, чтобы удалить его:", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("del_rev_"))
async def delete_single_review_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещен!", show_alert=True)
        return
    idx = int(callback.data.replace("del_rev_", ""))
    delete_review_by_index(idx)
    await callback.answer("✅ Отзыв успешно удален!")
    
    reviews = get_reviews_list()
    if not reviews:
        await callback.message.edit_text("💬 Все отзывы удалены.", parse_mode='HTML', reply_markup=admin_keyboard())
        return
    
    kb = []
    for i, rev in enumerate(reviews):
        short_text = rev[:30] + "..." if len(rev) > 30 else rev
        kb.append([InlineKeyboardButton(text=f"❌ Удалить: {short_text}", callback_data=f"del_rev_{i}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад в админку", callback_data="back_admin")])
    
    await callback.message.edit_text("🗑 <b>Управление отзывами:</b>", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "back_admin")
async def back_admin_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.edit_text("🔐 <b>Панель администратора</b>", parse_mode='HTML', reply_markup=admin_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещен!", show_alert=True)
        return
    await state.set_state(BroadcastState.waiting_for_message)
    await callback.message.edit_text("📢 Отправьте сообщение (текст, фото с описанием или видео) для рассылки всем пользователям:")
    await callback.answer()

@dp.message(BroadcastState.waiting_for_message)
async def send_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    success = 0
    for uid in get_all_users():
        try: 
            await message.send_copy(chat_id=uid)
            success += 1
        except: 
            pass
    await message.answer(f"✅ Рассылка завершена! Успешно отправлено: {success}", reply_markup=main_menu())

@dp.message(F.text == "🏋️ 🧬 Базовые протоколы")
async def basic_menu_msg(message: Message):
    await message.answer("Базовые протоколы:", reply_markup=basic_keyboard())

@dp.message(F.text == "🔥 Персональные программы")
async def personal_menu_msg(message: Message):
    await message.answer("Персональные программы:", reply_markup=personal_keyboard())

@dp.message(F.text == "💎 Купить оценки / Магазин")
async def shop_menu_msg(message: Message):
    user_id = message.from_user.id
    balance = USER_BALANCES.get(user_id, 5)
    await message.answer(f"💎 <b>Магазин оценок</b>\n\nВаш текущий баланс: <b>{balance}</b> оценок.", parse_mode='HTML', reply_markup=shop_eval_keyboard())

@dp.message(F.text == "💬 Отзывы")
async def show_reviews_msg(message: Message):
    reviews = get_reviews_list()
    text = "💬 <b>Отзывы клиентов:</b>\n\n" + ("\n\n".join(reviews) if reviews else "Пока нет ни одного отзыва. Будьте первыми!")
    await message.answer(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="leave_review")]
    ]))

@dp.callback_query(F.data == "leave_review")
async def start_leave_review(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not has_user_purchased(user_id) and user_id != ADMIN_ID:
        await callback.answer("❌ Оставлять отзывы могут только те пользователи, которые приобрели услуги в нашем боте!", show_alert=True)
        return
    
    await state.set_state(ReviewState.waiting_for_review_text)
    await callback.message.answer("Напишите ваш отзыв одним сообщением:")
    await callback.answer()

@dp.message(ReviewState.waiting_for_review_text)
async def process_review_text(message: Message, state: FSMContext):
    save_review(message.from_user.username or message.from_user.first_name, message.text)
    await state.clear()
    await message.answer("✅ Спасибо за отзыв!", reply_markup=main_menu())

@dp.callback_query(F.data == 'back_main')
async def back_handler(callback: CallbackQuery):
    try:
        await callback.message.edit_text('⚡ <b>АЛЬФА-МАССА</b>\n\nГлавное меню:', parse_mode='HTML')
        await callback.message.answer("Главное меню:", reply_markup=main_menu())
    except Exception:
        await callback.message.answer("Главное меню:", reply_markup=main_menu())
    await callback.answer()@dp.callback_query(F.data.startswith('buy_'))
async def buy_item_cb(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    item_key = callback.data.replace('buy_', '')
    
    if item_key not in PRODUKTIB:
        await callback.answer("❌ Товар не найден!", show_alert=True)
        return
        
    item = PRODUKTIB[item_key]
    
    if item['тип'] == 'eval':
        current_balance = USER_BALANCES.get(user_id, 5)
        USER_BALANCES[user_id] = current_balance + item['count']
        record_purchase(user_id)
        await callback.answer(f"✅ Успешно! Вам добавлено {item['count']} оценок формы.", show_alert=True)
        await callback.message.edit_text(
            f"💎 <b>Покупка успешна!</b>\n\nВам начислено: <b>{item['count']} оценок</b>.\nТекущий баланс: <b>{USER_BALANCES[user_id]}</b>", 
            parse_mode='HTML', 
            reply_markup=shop_eval_keyboard()
        )
        return

    if item['тип'] in ['personal_30', 'personal_year']:
        await state.update_data(prog_type=item_key)
        await state.set_state(ProgramStates.goal)
        await callback.message.answer(
            "🎯 <b>Оформление персональной программы</b>\n\nШаг 1/8: Напишите вашу главную цель (например: набор массы, сушка, рекомпозиция, увеличение роста):", 
            parse_mode='HTML'
        )
        await callback.answer()
        return

    prices = [LabeledPrice(label=item['title'], amount=item['cena'])]
    try:
        await bot.send_invoice(
            chat_id=user_id,
            title=item['title'],
            description=f"Приобретение методики/программы «{item['title']}» в ALPHA MASS",
            payload=f"pay_{item_key}",
            currency="XTR",
            prices=prices
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"❌ Ошибка создания счета: {e}", show_alert=True)

@dp.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def success_payment_handler(message: Message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    record_purchase(user_id)
    
    item_key = payload.replace("pay_", "")
    
    materials = {
        'сухой': "🧬 <b>Ваш материал по Сушке:</b>\n\n(Здесь находится ссылка на закрытый канал или гайд: https://t.me/+example_link_dry)",
        'масса': "🔥 <b>Ваш материал по Массонабору:</b>\n\n(Здесь находится ссылка на гайд по массе: https://t.me/+example_link_mass)",
        'rost': "📈 <b>Ваш материал по Альфа-Росту:</b>\n\n(Здесь находится ссылка на методику роста: https://t.me/+example_link_rost)",
        'rustam': "📜 <b>Ваш материал (Методика Р. Ахметова):</b>\n\n(Здесь находится ссылка: https://t.me/+example_link_rustam)",
        'сертори': "⚡ <b>Ваш материал (Методика Сертори):</b>\n\n(Здесь находится ссылка: https://t.me/+example_link_sertori)"
    }
    
    if item_key in materials:
        await message.answer(
            f"🎉 <b>Оплата прошла успешно! Спасибо за покупку!</b>\n\n{materials[item_key]}", 
            parse_mode='HTML', 
            reply_markup=main_menu()
        )
    else:
        await message.answer("🎉 Оплата прошла успешно! Администратор свяжется с вами для выдачи материала.", reply_markup=main_menu())

@dp.message(ProgramStates.goal)
async def prog_goal(message: Message, state: FSMContext):
    await state.update_data(goal=message.text)
    await state.set_state(ProgramStates.age)
    await message.answer("Шаг 2/8: Укажите ваш возраст:")

@dp.message(ProgramStates.age)
async def prog_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await state.set_state(ProgramStates.height)
    await message.answer("Шаг 3/8: Укажите ваш рост (в см):")

@dp.message(ProgramStates.height)
async def prog_height(message: Message, state: FSMContext):
    await state.update_data(height=message.text)
    await state.set_state(ProgramStates.weight)
    await message.answer("Шаг 4/8: Укажите ваш вес (в кг):")

@dp.message(ProgramStates.weight)
async def prog_weight(message: Message, state: FSMContext):
    await state.update_data(weight=message.text)
    await state.set_state(ProgramStates.experience)
    await message.answer("Шаг 5/8: Ваш стаж тренировок (сколько занимаетесь):")

@dp.message(ProgramStates.experience)
async def prog_experience(message: Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await state.set_state(ProgramStates.conditions)
    await message.answer("Шаг 6/8: Где занимаетесь (зал / дома со своим весом / дома с гантелями)?")

@dp.message(ProgramStates.conditions)
async def prog_conditions(message: Message, state: FSMContext):
    await state.update_data(conditions=message.text)
    await state.set_state(ProgramStates.injuries)
    await message.answer("Шаг 7/8: Есть ли травмы, ограничения по здоровью или хронические боли?")

@dp.message(ProgramStates.injuries)
async def prog_injuries(message: Message, state: FSMContext):
    await state.update_data(injuries=message.text)
    await state.set_state(ProgramStates.supplements)
    await message.answer("Шаг 8/8: Принимаете ли спортивное питание или фарм. поддержку (если да, то что)?")

@dp.message(ProgramStates.supplements)
async def prog_supplements(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    await state.clear()
    
    prog_type = data.get('prog_type')
    item_info = PRODUKTIB.get(prog_type, {'title': 'Персональная программа', 'cena': 149})
    
    summary = (
        "📋 <b>Анкета для персональной программы успешно заполнена!</b>\n\n"
        f"🎯 Цель: {data.get('goal')}\n"
        f"👶 Возраст: {data.get('age')}\n"
        f"📏 Рост: {data.get('height')} см\n"
        f"⚖️ Вес: {data.get('weight')} кг\n"
        f"⏳ Стаж: {data.get('experience')}\n"
        f"🏠 Условия: {data.get('conditions')}\n"
        f"⚠️ Травмы: {data.get('injuries')}\n"
        f"💊 Добавки: {message.text}\n"
    )
    await message.answer(summary, parse_mode='HTML')
    
    prices = [LabeledPrice(label=item_info['title'], amount=item_info['cena'])]
    try:
        await bot.send_invoice(
            chat_id=user_id,
            title=item_info['title'],
            description=f"Оплата персональной программы: {item_info['title']}",
            payload=f"pay_{prog_type}",
            currency="XTR",
            prices=prices
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка выставления счета: {e}", reply_markup=main_menu())

@dp.message(F.text == "📊 Оценка формы по фото")
async def evaluate_form_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    balance = USER_BALANCES.get(user_id, 5)
    
    if balance <= 0 and user_id != ADMIN_ID:
        await message.answer(
            "❌ <b>У вас закончились оценки формы!</b>\n\nПополните баланс в магазине или пригласите друзей по реферальной ссылке.", 
            parse_mode='HTML', 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Купить оценки", callback_data="goto_shop")],
                [InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="goto_ref")],
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_main")]
            ])
        )
        return

    USER_PHOTOS[user_id] = []
    await state.set_state(FormStates.waiting_for_photos)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Запустить анализ формы", callback_data="run_ai_analysis")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_main")]
    ])
    
    await message.answer(
        "📊 <b>Оценка формы по фотографии</b>\n\n"
        "Отправьте от <b>1 до 5 фотографий</b> вашей текущей формы (с разных ракурсов: спереди, сбоку, сзади).\n\n"
        "<i>Как только закончите отправку фото, нажмите кнопку <b>«🚀 Запустить анализ формы»</b> ниже:</i>", 
        parse_mode='HTML', 
        reply_markup=kb
    )

@dp.message(FormStates.waiting_for_photos, F.photo)
async def handle_user_photos(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in USER_PHOTOS:
        USER_PHOTOS[user_id] = []
        
    if len(USER_PHOTOS[user_id]) >= 5:
        await message.answer("⚠️ Вы уже загрузили максимальное количество фотографий (5 штук). Нажмите «Запустить анализ формы».")
        return
        
    photo = message.photo[-1]
    file_id = photo.file_id
    USER_PHOTOS[user_id].append(file_id)
    
    count = len(USER_PHOTOS[user_id])
    await message.answer(f"✅ Фото #{count} успешно добавлено! (Загружено: {count}/5). Отправьте еще или запустите анализ.")

@dp.callback_query(FormStates.waiting_for_photos, F.data == "run_ai_analysis")
async def run_ai_analysis_cb(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    photos = USER_PHOTOS.get(user_id, [])
    
    if not photos:
        await callback.answer("❌ Вы не загрузили ни одной фотографии!", show_alert=True)
        return
        
    balance = USER_BALANCES.get(user_id, 5)
    if balance <= 0 and user_id != ADMIN_ID:
        await callback.answer("❌ Недостаточно оценок на балансе!", show_alert=True)
        await state.clear()
        return
        
    if user_id != ADMIN_ID:
        USER_BALANCES[user_id] = balance - 1
        
    await state.clear()
    await callback.message.edit_text("⏳ <b>ИИ проводит детальный анализ вашей формы...</b>\n\nОцениваем пропорции, дефицитные мышечные группы, уровень сухости/жиропрослойки и даем рекомендации. Подождите 10-20 секунд.", parse_mode='HTML')
    
    try:
        image_parts = []
        for file_id in photos:
            file = await bot.get_file(file_id)
            file_path = file.file_path
            downloaded_file = await bot.download_file(file_path)
            image_bytes = downloaded_file.read()
            image_parts.append({
                'mime_type': 'image/jpeg',
                'data': image_bytes
            })
            
        prompt = (
            "Ты — профессиональный элитный фитнес-тренер, судья по бодибилдингу и эксперт по телостроительству. "
            "Проведи жесткий, но конструктивный и детальный анализ физической формы пользователя по предоставленным фотографиям. "
            "Выдели: 1. Сильные стороны и развитые мышечные группы. 2. Отстающие зоны, над которыми нужно работать в первую очередь. "
            "3. Примерный процент жира в организме. 4. Конкретные рекомендации по тренировкам и питанию для прогресса. "
            "Ответ пиши структурированно, профессионально и мотивирующе на русском языке."
        )
        
        contents = [prompt] + image_parts
        
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents
        )
        
        analysis_text = response.text
        
        remaining_balance = USER_BALANCES.get(user_id, 5)
        final_text = (
            "📊 <b>Результаты анализа вашей формы от ИИ-тренера:</b>\n\n"
            f"{analysis_text}\n\n"
            f"💎 <i>Осталось оценок на балансе: {remaining_balance}</i>"
        )
        
        await bot.send_message(user_id, final_text, parse_mode='HTML', reply_markup=main_menu())
        
    except Exception as e:
        await bot.send_message(user_id, f"❌ Произошла ошибка при обращении к ИИ-модели: {e}", reply_markup=main_menu())
    
    if user_id in USER_PHOTOS:
        USER_PHOTOS[user_id] = []

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
  
  
