import asyncio
import logging
import os
from threading import Thread
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from google import genai
from flask import Flask

# --- 1. Мини-сервер Flask для Render ---
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

# --- 2. Конфигурация бота и ИИ (ключи берутся из секретов сервера) ---
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

CHANNEL_USERNAME = "@alphamasss"
ADMIN_ID = 7847949636

bot = Bot(token=BOT_TOKEN)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
dp = Dispatcher()

# --- Базы данных (файлы) ---
USERS_FILE = "users.txt"
REVIEWS_FILE = "reviews.txt"

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

def save_review(user_name: str, text: str):
    with open(REVIEWS_FILE, "a", encoding="utf-8") as f:
        f.write(f"@{user_name}: {text}\n---\n")

def get_all_reviews() -> str:
    if not os.path.exists(REVIEWS_FILE):
        return " Пока нет ни одного отзыва. Будьте первыми!"
    with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
    return content if content else " Пока нет ни одного отзыва."

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
# --- 3. FSM (Состояния) ---
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

# --- 4. Клавиатуры ---
def get_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/alphamasss")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
    ])

def main_menu(user_id: int = 0):
    kb = [
        [KeyboardButton(text="📊 Оценка формы по фото"), KeyboardButton(text="🏋️ 🧬 Базовые протоколы")],
        [KeyboardButton(text="🔥 Персональные программы"), KeyboardButton(text="💎 Купить оценки / Магазин")],
        [KeyboardButton(text="💬 Отзывы")]
    ]
    if user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="📢 Сделать рассылку")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def basic_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Сушка – 49 ⭐', callback_data='buy_сухой')],
        [InlineKeyboardButton(text='Массонабор – 49 ⭐', callback_data='buy_масса')],
        [InlineKeyboardButton(text='Альфа-Рост – 99 ⭐', callback_data='buy_rost')],
        [InlineKeyboardButton(text='Методика Р. Ахметова – 99 ⭐', callback_data='buy_rustam')],
        [InlineKeyboardButton(text='Методика Сертори – 99 ⭐', callback_data='buy_сертори')],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_main')],
    ])

def personal_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Программа 30 дней – 149 ⭐', callback_data='buy_pers_30')],
        [InlineKeyboardButton(text='Программа на год – 499 ⭐', callback_data='buy_pers_year')],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_main')],
    ])

def shop_eval_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='1 оценка – 3 ⭐', callback_data='buy_eval_1')],
        [InlineKeyboardButton(text='5 оценок – 15 ⭐', callback_data='buy_eval_5')],
        [InlineKeyboardButton(text='10 оценок – 30 ⭐', callback_data='buy_eval_10')],
        [InlineKeyboardButton(text='30 оценок – 90 ⭐', callback_data='buy_eval_30')],
        [InlineKeyboardButton(text='50 оценок – 150 ⭐', callback_data='buy_eval_50')],
        [InlineKeyboardButton(text='100 оценок – 300 ⭐', callback_data='buy_eval_100')],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_main')]
    ])
# --- 5. Логика бота ---
async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
        return False

@dp.message(CommandStart())
async def start_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    add_user(user_id)
    if not await check_subscription(bot, user_id):
        await message.answer("⚡ <b>АЛЬФА-МАССА</b>\n\nДля доступа подпишитесь на канал:", reply_markup=get_sub_keyboard(), parse_mode='HTML')
        return
    if user_id not in USER_BALANCES:
        USER_BALANCES[user_id] = 5
    await message.answer("⚡ <b>АЛЬФА-МАССА</b>\n\nГлавное меню:", reply_markup=main_menu(user_id), parse_mode='HTML')

@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    add_user(user_id)
    if await check_subscription(bot, user_id):
        if user_id not in USER_BALANCES:
            USER_BALANCES[user_id] = 5
        await callback.message.edit_text("✅ Подписка подтверждена!")
        await callback.message.answer("Главное меню:", reply_markup=main_menu(user_id), parse_mode='HTML')
    else:
        await callback.answer("❌ Вы еще не подписались!", show_alert=True)

@dp.message(F.text == "🏋️ 🧬 Базовые протоколы")
async def basic_menu_msg(message: Message):
    await message.answer("Базовые протоколы:", reply_markup=basic_keyboard())

@dp.message(F.text == "🔥 Персональные программы")
async def personal_menu_msg(message: Message):
    await message.answer("Персональные программы:", reply_markup=personal_keyboard())

@dp.message(F.text == "💎 Купить оценки / Магазин")
async def shop_menu_msg(message: Message):
    user_id = message.from_user.id
    balance = USER_BALANCES.get(user_id, 0)
    await message.answer(f"Баланс: {balance} оценок.", reply_markup=shop_eval_keyboard())

@dp.message(F.text == "💬 Отзывы")
async def show_reviews_msg(message: Message):
    await message.answer(get_all_reviews(), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="leave_review")]
    ]))

@dp.callback_query(F.data == "leave_review")
async def start_leave_review(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReviewState.waiting_for_review_text)
    await callback.message.answer("Напишите ваш отзыв одним сообщением:")
    await callback.answer()

@dp.message(ReviewState.waiting_for_review_text)
async def process_review_text(message: Message, state: FSMContext):
    save_review(message.from_user.username or message.from_user.first_name, message.text)
    await state.clear()
    await message.answer("✅ Спасибо за отзыв!", reply_markup=main_menu(message.from_user.id))

@dp.callback_query(F.data == 'back_main')
async def back_handler(callback: CallbackQuery):
    await callback.message.edit_text('Главное меню:', reply_markup=main_menu(callback.from_user.id))
    await callback.answer()

# Оценка формы
@dp.message(F.text == "📊 Оценка формы по фото")
async def start_form_eval(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if USER_BALANCES.get(user_id, 0) <= 0:
        await message.answer("❌ Недостаточно оценок на балансе!")
        return
    USER_PHOTOS[user_id] = []
    await state.set_state(FormStates.waiting_for_photos)
    await message.answer("Отправьте до 5 фото и нажмите кнопку:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Готово к анализу", callback_data="analyze_photos")]
    ]))

@dp.message(FormStates.waiting_for_photos, F.photo)
async def collect_form_photos(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if len(USER_PHOTOS.get(user_id, [])) < 5:
        USER_PHOTOS[user_id].append(message.photo[-1].file_id)
        await message.answer(f"Фото добавлено ({len(USER_PHOTOS[user_id])}/5)")

@dp.callback_query(FormStates.waiting_for_photos, F.data == "analyze_photos")
async def execute_photo_analysis(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    photos = USER_PHOTOS.get(user_id, [])
    if not photos:
        await callback.answer("Сначала загрузите фото!", show_alert=True)
        return
    USER_BALANCES[user_id] -= 1
    await state.clear()
    await callback.message.edit_text("🔄 Анализируем форму через ИИ...")
    try:
        content_parts = ["Проанализируй форму спортсмена:"]
        for pid in photos:
            file_info = await bot.get_file(pid)
            file_io = await bot.download_file(file_info.file_path)
            content_parts.append(genai.types.Part.from_bytes(data=file_io.read(), mime_type="image/jpeg"))
        response = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=content_parts)
        await bot.send_message(user_id, response.text, reply_markup=main_menu(user_id))
    except Exception as e:
        USER_BALANCES[user_id] += 1
        await bot.send_message(user_id, f"⚠️ Ошибка анализа: {e}", reply_markup=main_menu(user_id))

# Анкета для программ
@dp.callback_query(F.data.in_({'buy_pers_30', 'buy_pers_year'}))
async def start_survey(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProgramStates.goal)
    await callback.message.edit_text("Укажите вашу цель:")
    await callback.answer()

@dp.message(ProgramStates.goal)
async def survey_goal(message: Message, state: FSMContext):
    await state.update_data(goal=message.text)
    await state.clear()
    await message.answer("⏳ Генерируем программу...")
    response = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=f"Составь программу под цель: {message.text}")
    await message.answer(response.text, reply_markup=main_menu(message.from_user.id))

# Рассылка
@dp.message(F.text == "📢 Сделать рассылку")
async def admin_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: 
        return
    await state.set_state(BroadcastState.waiting_for_message)
    await message.answer("Отправьте сообщение для рассылки:")

@dp.message(BroadcastState.waiting_for_message)
async def send_broadcast(message: Message, state: FSMContext):
    await state.clear()
    for uid in get_all_users():
        try: 
            await message.send_copy(chat_id=uid)
        except: 
            pass
    await message.answer("✅ Рассылка завершена!", reply_markup=main_menu(message.from_user.id))

# Платежи
@dp.callback_query(F.data.startswith('buy_'))
async def buy_handler(callback: CallbackQuery):
    p = PRODUKTIB.get(callback.data.replace('buy_', '', 1))
    if p:
        await callback.message.answer_invoice(
            title=p['title'], description=p['title'], payload=callback.data,
            currency='XTR', prices=[LabeledPrice(label=p['title'], amount=p['цена'])]
        )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(q.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    p = PRODUKTIB.get(message.successful_payment.invoice_payload.replace('buy_', '', 1), {})
    if p.get('тип') == 'eval':
        USER_BALANCES[message.from_user.id] = USER_BALANCES.get(message.from_user.id, 0) + p.get('count', 0)
    await message.answer("✅ Оплата прошла успешно!", reply_markup=main_menu(message.from_user.id))

# Запуск
async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
      
