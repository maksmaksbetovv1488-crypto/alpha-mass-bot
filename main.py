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
)
from flask import Flask

# --- 1. Мини-сервер Flask для Render (держит порт открытым) ---
app = Flask('')


@app.route('/')
def home():
  return 'ALPHA MASS Bot is active!'


def run_flask():
  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  t = Thread(target=run_flask)
  t.start()


# --- 2. Основной код твоего бота ---
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = '8863657412:AAFtDGoxddMmOoi0f7hCUoELbYdzx-rprdU'
ADMIN_USERNAME = 'Alphamash'

dp = Dispatcher()

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
    'pers_30': {'title': 'Программа 30 дней', 'цена': 149, 'type': 'personal'},
    'pers_year': {'title': 'Программа на год', 'цена': 499, 'type': 'personal'},
}


def main_keyboard():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text='🏋️ 🧬 Базовые протоколы', callback_data='category_basic'
              )
          ],
          [
              InlineKeyboardButton(
                  text='🔥 Персональные программы',
                  callback_data='category_personal',
              )
          ],
      ]
  )


def basic_keyboard():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text='Сушка – 49 ⭐', callback_data='buy_dry')],
          [
              InlineKeyboardButton(
                  text='Массонабор – 49 ⭐', callback_data='buy_mass'
              )
          ],
          [
              InlineKeyboardButton(
                  text='Альфа-Рост – 99 ⭐', callback_data='buy_rost'
              )
          ],
          [
              InlineKeyboardButton(
                  text='Методика Сертори – 99 ⭐', callback_data='buy_sertori'
              )
          ],
          [InlineKeyboardButton(text='🔙 Назад', callback_data='back_main')],
      ]
  )


def personal_keyboard():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text='Программа 30 дней – 149 ⭐',
                  callback_data='buy_pers_30',
              )
          ],
          [
              InlineKeyboardButton(
                  text='Программа на год – 499 ⭐',
                  callback_data='buy_pers_year',
              )
          ],
          [InlineKeyboardButton(text='🔙 Назад', callback_data='back_main')],
      ]
  )


@dp.message(CommandStart())
async def start_handler(message: Message):
  await message.answer(
      '⚡ <b>АЛЬФА-МАССА</b> \n\n Выберите параметр:',
      reply_markup=main_keyboard(),
      parse_mode='HTML',
  )


@dp.callback_query(F.data == 'category_basic')
async def basic_handler(callback: CallbackQuery):
  await callback.message.edit_text(
      '🏋️ 🧬<b>Базовые протоколы</b> \n\n Выберите продукт:',
      reply_markup=basic_keyboard(),
      parse_mode='HTML',
  )
  await callback.answer()


@dp.callback_query(F.data == 'category_personal')
async def personal_handler(callback: CallbackQuery):
  await callback.message.edit_text(
      '🔥 <b>Персональные программы</b> \n\n Выберите продукт:',
      reply_markup=personal_keyboard(),
      parse_mode='HTML',
  )
  await callback.answer()


@dp.callback_query(F.data == 'back_main')
async def back_handler(callback: CallbackQuery):
  await callback.message.edit_text(
      '⚡ <b>АЛЬФА-МАССА</b> \n\n Выберите параметр:',
      reply_markup=main_keyboard(),
      parse_mode='HTML',
  )
  await callback.answer()


@dp.callback_query(F.data.startswith('buy_'))
async def product_handler(callback: CallbackQuery):
  payload = callback.data.replace('buy_', '', 1)
  product = PRODUKTIB.get(payload, PRODUKTIB['сухой'])
  await callback.message.answer_invoice(
      title=product['title'],
      description=f"Оплата {product['title']}",
      payload=payload,
      currency='XTR',
      prices=[LabeledPrice(label=product['title'], amount=product['цена'])],
  )
  await callback.answer()


@dp.pre_checkout_query()
async def pre_checkout_query_handler(query: PreCheckoutQuery):
  await query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message, bot: Bot):
  payload = message.successful_payment.invoice_payload
  product = PRODUKTIB.get(payload, PRODUKTIB['сухой'])

  if product.get('type') == 'personal':
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='💬 Написать автору',
                    url=f'https://t.me/{ADMIN_USERNAME}',
                )
            ]
        ]
    )
    await message.answer(
        f"✅ <b>Оплата успешно получена!</b> \n\n🔥 Вы приобрели:"
        f" <b>{product['title']}</b>\n\nТеперь нажмите на кнопку ниже, чтобы"
        ' написать мне в личные сообщения и начать работу!',
        reply_markup=keyboard,
        parse_mode='HTML',
    )
  else:
    try:
      channel_id = product.get('канал')
      invite = await bot.create_chat_invite_link(
          chat_id=channel_id, member_limit=1
      )
      await message.answer(
          f"✅ <b>Оплата получена!</b> \n\n 📦 <b>{product['title']}</b> \n\n Ссылка"
          f' на канал: {invite.invite_link}',
          parse_mode='HTML',
      )
    except Exception as e:
      await message.answer('Ошибка создания ссылки. Обратитесь к администратору.')


async def main():
  # Запускаем фоновый веб-сервер для Render
  keep_alive()
  print('⚡ Flask-сервер запущен в фоновом режиме')

  bot = Bot(token=BOT_TOKEN)
  print('⚡ Альфа-МАССА-БОТ запущен!')
  await dp.start_polling(bot)


if __name__ == '__main__':
  asyncio.run(main())
