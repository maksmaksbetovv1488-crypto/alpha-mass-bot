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

# --- 2. Конфигурация бота и ИИ ---
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = '8863657412:AAFtDGoxddMmOoi0f7hCUoELbYdzx-rprdU'
CHANNEL_USERNAME = "@alphamasss"
ADMIN_ID = 7847949636

bot = Bot(token=BOT_TOKEN)
gemini_client = genai.Client()
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
    'сухой': {
        'title': 'Сушка',
        'цена': 49,
        'канал': -1004395381148,
        'type': 'channel',
    },
    'масса': {
        'title': 'Массонабор',
        'цена': 49,
        'канал': -1004372480639,
        'type': 'channel',
    },
    'rost': {
        'title': 'Альфа-Рост',
        'цена': 99,
        'канал': -100442056365,
        'type': 'channel',
    },
    'rustam': {
        'title': 'Методика Р. Ахметова',
        'цена': 99,
        'канал': -1004342066932,
        'type': 'channel',
    },
    'сертори': {
        'title': 'Методика Сертори',
        'цена': 99,
        'канал': -1003701087960,
        'type': 'channel',
    },
    'pers_30': {'title': 'Программа 30 дней', 'цена': 149, 'type': 'personal_30'},
    'pers_year': {'title': 'Программа на год', 'цена': 499, 'type': 'personal_year'},
    'eval_1': {'title': '1 оценка формы', 'цена': 3, 'type': 'eval', 'count': 1},
    'eval_5': {'title': '5 оценок формы', 'цена': 15, 'type': 'eval', 'count': 5},
    'eval_10': {'title': '10 оценок формы', 'цена': 30, 'type': 'eval', 'count': 10},
    'eval_30': {'title': '30 оценок формы', 'цена': 90, 'type': 'eval', 'count': 30},
    'eval_50': {'title': '50 оценок формы', 'цена': 150, 'type': 'eval', 'count': 50},
    'eval_100': {'title': '100 оценок формы', 'цена': 300, 'type': 'eval', 'count': 100},
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
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text='Сушка – 49 ⭐', callback_data='buy_сухой')],
          [InlineKeyboardButton(text='Массонабор – 49 ⭐', callback_data='buy_масса')],
          [InlineKeyboardButton(text='Альфа-Рост – 99 ⭐', callback_data='buy_rost')],
          [InlineKeyboardButton(text='Методика Р. Ахметова – 99 ⭐', callback_data='buy_rustam')],
          [InlineKeyboardButton(text='Методика Сертори – 99 ⭐', callback_data='buy_сертори')],
          [InlineKeyboardButton(text='🔙 Назад', callback_data='back_main')],
      ]
  )

def personal_keyboard():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text='Программа 30 дней – 149 ⭐', callback_data='buy_pers_30')],
          [InlineKeyboardButton(text='Программа на год – 499 ⭐', callback_data='buy_pers_year')],
          [InlineKeyboardButton(text='🔙 Назад', callback_data='back_main')],
      ]
  )

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

# --- 5. Проверка подписки ---
async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
        return False

# --- 6. Хендлеры /start и подписки ---
@dp.message(CommandStart())
async def start_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    add_user(user_id)

    if not await check_subscription(bot, user_id):
        await message.answer(
            "⚡ <b>АЛЬФА-МАССА</b>\n\nДля доступа к боту необходимо подписаться на наш официальный канал:",
            reply_markup=get_sub_keyboard(),
            parse_mode='HTML'
        )
        return

    if user_id not in USER_BALANCES:
        USER_BALANCES[user_id] = 5

    await message.answer(
        "⚡ <b>АЛЬФА-МАССА</b> \n\nВыберите нужный раздел в меню ниже:",
        reply_markup=main_menu(user_id),
        parse_mode='HTML',
    )

@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    add_user(user_id)
    
    if await check_subscription(bot, user_id):
        if user_id not in USER_BALANCES:
            USER_BALANCES[user_id] = 5
        await callback.message.edit_text("✅ Подписка подтверждена! Бот разблокирован.")
        await callback.message.answer("⚡ <b>АЛЬФА-МАССА</b> \n\nГлавное меню:", reply_markup=main_menu(user_id), parse_mode='HTML')
    else:
        await callback.answer("❌ Вы еще не подписались на канал!", show_alert=True)

# --- 7. Навигация и отзывы ---
@dp.message(F.text == "🏋️ 🧬 Базовые протоколы")
async def basic_menu_msg(message: Message):
    await message.answer("🏋️ 🧬 <b>Базовые протоколы</b> \n\nВыберите продукт:", reply_markup=basic_keyboard(), parse_mode='HTML')

@dp.callback_query(F.data == 'category_basic')
async def basic_handler(callback: CallbackQuery):
  await callback.message.edit_text(
      '🏋️ 🧬 <b>Базовые протоколы</b> \n\n Выберите продукт:',
      reply_markup=basic_keyboard(),
      parse_mode='HTML',
  )
  await callback.answer()

@dp.message(F.text == "🔥 Персональные программы")
async def personal_menu_msg(message: Message):
    await message.answer("🔥 <b>Персональные программы</b> \n\nВыберите вариант:", reply_markup=personal_keyboard(), parse_mode='HTML')

@dp.callback_query(F.data == 'category_personal')
async def personal_handler(callback: CallbackQuery):
  await callback.message.edit_text(
      '🔥 <b>Персональные программы</b> \n\n Выберите продукт:',
      reply_markup=personal_keyboard(),
      parse_mode='HTML',
  )
  await callback.answer()

@dp.message(F.text == "💎 Купить оценки / Магазин")
async def shop_menu_msg(message: Message):
    user_id = message.from_user.id
    balance = USER_BALANCES.get(user_id, 0)
    await message.answer(
        f"💎 <b>МАГАЗИН И ПЛАТНЫЕ УСЛУГИ</b>\n\n"
        f"Ваш текущий баланс оценок формы: <b>{balance}</b>\n\n"
        f"Выберите пакет для покупки:",
        reply_markup=shop_eval_keyboard(),
        parse_mode='HTML'
    )

@dp.message(F.text == "💬 Отзывы")
async def show_reviews_msg(message: Message):
    reviews_text = get_all_reviews()
    await message.answer(
        f"💬 <b>ОТЗЫВЫ НАШИХ ПОЛЬЗОВАТЕЛЕЙ</b>\n\n{reviews_text}",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="leave_review")]
        ])
    )

@dp.callback_query(F.data == "leave_review")
async def start_leave_review(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReviewState.waiting_for_review_text)
    await callback.message.answer(
        "✍️ Напишите ваш отзыв о боте, программах или оценке формы одним сообщением:"
    )
    await callback.answer()

@dp.message(ReviewState.waiting_for_review_text)
async def process_review_text(message: Message, state: FSMContext):
    user_name = message.from_user.username or message.from_user.first_name
    save_review(user_name, message.text)
    await state.clear()
    
    user_id = message.from_user.id
    await message.answer(
        "✅ **Спасибо за ваш отзыв!** Он добавлен в общий раздел отзывов.",
        reply_markup=main_menu(user_id),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == 'back_main')
async def back_handler(callback: CallbackQuery):
  user_id = callback.from_user.id
  await callback.message.edit_text(
      '⚡ <b>АЛЬФА-МАССА</b> \n\n Выберите параметр:',
      reply_markup=main_menu(user_id),
      parse_mode='HTML',
  )
  await callback.answer()

# --- 8. ОЦЕНКА ФОРМЫ ---
@dp.message(F.text == "📊 Оценка формы по фото")
async def start_form_eval(message: Message, state: FSMContext):
    user_id = message.from_user.id
    balance = USER_BALANCES.get(user_id, 0)
    if balance <= 0:
        await message.answer(
            "❌ У вас закончились бесплатные оценки формы!\n"
            "Вы можете приобрести дополнительные оценки в магазине:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Купить оценки", callback_data="buy_eval_5")],
                [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
            ])
        )
        return

    USER_PHOTOS[user_id] = []
    await state.set_state(FormStates.waiting_for_photos)
    await message.answer(
        "📸 <b>Оценка формы от ИИ-эксперта</b>\n\n"
        "Отправьте **до 5 фотографий** вашей формы с разных ракурсов (спереди, сзади, сбоку и т.д.).\n"
        "Когда скинете все нужные ракурсы, нажмите кнопку **«✅ Готово к анализу»**.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово к анализу", callback_data="analyze_photos")]
        ]),
        parse_mode='HTML'
    )

@dp.message(FormStates.waiting_for_photos, F.photo)
async def collect_form_photos(message: Message, state: FSMContext):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    if user_id not in USER_PHOTOS:
        USER_PHOTOS[user_id] = []
    
    if len(USER_PHOTOS[user_id]) >= 5:
        await message.answer("⚠️ Вы уже прикрепили максимум 5 фото для этой оценки! Нажмите «Готово к анализу».")
        return
        
    USER_PHOTOS[user_id].append(photo_id)
    count = len(USER_PHOTOS[user_id])
    await message.answer(f"📷 Фото #{count} из 5 добавлено. Можете скинуть следующий ракурс или нажать «Готово к анализу».")

@dp.callback_query(FormStates.waiting_for_photos, F.data == "analyze_photos")
async def execute_photo_analysis(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    photos = USER_PHOTOS.get(user_id, [])
    if not photos:
        await callback.answer("❌ Вы не прикрепили ни одной фотографии!", show_alert=True)
        return

    USER_BALANCES[user_id] -= 1
    await state.clear()
    await callback.message.edit_text("🔄 ИИ проводит детальный анатомический анализ вашей формы по всем ракурсам и мышцам... Пожалуйста, подождите (около 15 секунд).")

    prompt = (
        "Ты — профессиональный элитный фитнес-тренер, спортивный нутрициолог и судья по бодибилдингу с 10-летним стажем. "
        "Проведи максимально жесткий, детальный и экспертный анализ физической формы человека по предоставленным фотографиям со всех ракурсов. "
        "Структура ответа:\n"
        "1. Общий вердикт и уровень.\n"
        "2. Детальный разбор по зонам и ракурсам.\n"
        "3. Что конкретно стоит сделать.\n"
        "4. Рекомендация программ из каталога."
    )

    try:
        content_parts = [prompt]
        for pid in photos:
            file_info = await bot.get_file(pid)
            file_bytes = await bot.download_file(file_info.file_path)
            content_parts.append(genai.types.Part.from_bytes(data=file_bytes, mime_type="image/jpeg"))

        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=content_parts
        )
        
        recommendation_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Заказать персональную программу", callback_data="buy_pers_30")],
            [InlineKeyboardButton(text="🏋️ Посмотреть базовые протоколы", callback_data="category_basic")],
            [InlineKeyboardButton(text="💎 Купить еще оценки", callback_data="buy_eval_5")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
        ])

        await bot.send_message(
            user_id, 
            f"📋 <b>ЭКСПЕРТНЫЙ АНАЛИЗ ФОРМЫ И РЕКОМЕНДАЦИИ</b>\n\n{response.text}\n\n💡 Осталось оценок на балансе: <b>{USER_BALANCES[user_id]}</b>", 
            reply_markup=recommendation_markup, 
            parse_mode='HTML'
        )
    except Exception as e:
        logging.error(f"Ошибка анализа фото: {e}")
        USER_BALANCES[user_id] += 1
        await bot.send_message(user_id, "⚠️ Произошла ошибка при анализе фотографий. Ваша оценка возвращена на баланс.", reply_markup=main_menu(user_id))

# --- 9. Анкетирование для программ ---
@dp.callback_query(F.data.in_({'buy_pers_30', 'buy_pers_year'}))
async def start_program_survey(callback: CallbackQuery, state: FSMContext):
    prog_type = '30_days' if callback.data == 'buy_pers_30' else 'year'
    await state.update_data(prog_type=prog_type)
    await state.set_state(ProgramStates.goal)
    await callback.message.edit_text(
        "📋 <b>АНКЕТА ЗАКАЗА (Шаг 1/8)</b>\n\nУкажите цель:\n• Массонабор\n• Сушка / Рельеф"
    )
    await callback.answer()

@dp.message(ProgramStates.goal)
async def survey_goal(message: Message, state: FSMContext):
    await state.update_data(goal=message.text)
    await state.set_state(ProgramStates.age)
    await message.answer("📋 <b>Шаг 2/8</b>\n\nУкажите ваш возраст:")

@dp.message(ProgramStates.age)
async def survey_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await state.set_state(ProgramStates.height)
    await message.answer("📋 <b>Шаг 3/8</b>\n\nУкажите рост (в см):")

@dp.message(ProgramStates.height)
async def survey_height(message: Message, state: FSMContext):
    await state.update_data(height=message.text)
    await state.set_state(ProgramStates.weight)
    await message.answer("📋 <b>Шаг 4/8</b>\n\nУкажите текущий вес (в кг):")

@dp.message(ProgramStates.weight)
async def survey_weight(message: Message, state: FSMContext):
    await state.update_data(weight=message.text)
    await state.set_state(ProgramStates.experience)
    await message.answer("📋 <b>Шаг 5/8</b>\n\nОпыт тренировок (Новичок / Средний / Опытный):")

@dp.message(ProgramStates.experience)
async def survey_exp(message: Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await state.set_state(ProgramStates.conditions)
    await message.answer("📋 <b>Шаг 6/8</b>\n\nУсловия тренировок (Зал / Дома / Свой вес):")

@dp.message(ProgramStates.conditions)
async def survey_cond(message: Message, state: FSMContext):
    await state.update_data(conditions=message.text)
    await state.set_state(ProgramStates.injuries)
    await message.answer("📋 <b>Шаг 7/8</b>\n\nОграничения / Травмы:")

@dp.message(ProgramStates.injuries)
async def survey_inj(message: Message, state: FSMContext):
    await state.update_data(injuries=message.text)
    await state.set_state(ProgramStates.supplements)
    await message.answer("📋 <b>Шаг 8/8</b>\n\nДоступный спортпит и добавки:")

@dp.message(ProgramStates.supplements)
async def survey_finish_and_generate(message: Message, state: FSMContext):
    await state.update_data(supplements=message.text)
    data = await state.get_data()
    await state.clear()
    user_id = message.from_user.id

    await message.answer("⏳ Элитный ИИ-тренер составляет вашу персональную экспертную программу...")

    prompt = f"Составь программу тренировок для клиента. Цель: {data.get('goal')}, Возраст: {data.get('age')}, Рост: {data.get('height')}, Вес: {data.get('weight')}"

    try:
        response = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        await message.answer(f"👑 <b>ПЕРСОНАЛЬНАЯ ПРОГРАММА ГОТОВА</b>\n\n{response.text}", reply_markup=main_menu(user_id), parse_mode='HTML')
    except Exception as e:
        logging.error(f"Ошибка генерации программы: {e}")
        await message.answer("⚠️ Произошла ошибка при генерации программы.", reply_markup=main_menu(user_id))

# --- 10. АДМИНКА: РАССЫЛКА (ИСПОЛЬЗУЮТСЯ ТРОЙНЫЕ КАВЫЧКИ) ---
@dp.message(F.text == "📢 Сделать рассылку")
async def admin_broadcast_prompt(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    await message.answer("""✍️ Отправьте или перешлите сообщение
для рассылки.""")
    await state.set_state(BroadcastState.waiting_for_message)

@dp.message(BroadcastState.waiting_for_message)
async def execute_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    await state.clear()
    users = get_all_users()
    
    if not users:
        await message.answer("❌ База пользователей пуста.")
        r
