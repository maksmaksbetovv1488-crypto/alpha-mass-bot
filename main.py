import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, PreCheckoutQuery, LabeledPrice

BOT_TOKEN = "8863657412:AAFtDGoxddMmOoi0f7hCUoELbYdzx-rprdU"
dp = Dispatcher()

PRODUKTIB = {
    "сухой" : { "title" : "Сушка", "цена" : 49, "канал" : - 1004395381148 },
    "масса" : { "title" : "Массонабор", "цена" : 49, "канал" : - 1004372480639 },
    "rost" : { "title" : "Альфа-Рост", "цена" : 99, "канал" : - 100442056365 },
    "rustam" : { "title" : "Методика Р. Ахметова", "цена" : 99, "канал" : - 1004342066932 },
    "сертори" : { "title" : "Методика Сертори", "цена" : 99, "канал" : - 1003701087960 },
    "pers_30" : { "title" : "Программа 30 дней", "цена" : 149, "канал" : - 1004342066932 },
    "pers_year" : { "title" : "Программа на год", "цена" : 499, "канал" : - 1004342066932 },
}

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏋️ 🧬 Базовые протоколы", callback_data="category_basic")],
        [InlineKeyboardButton(text="🔥 Персональные программы", callback_data="category_personal")]
    ])

def basic_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сушка – 49 XTR", callback_data="buy_dry")],
        [InlineKeyboardButton(text="Массонабор – 49 XTR", callback_data="buy_mass")],
        [InlineKeyboardButton(text="Альфа-Рост – 99 XTR", callback_data="buy_rost")],
        [InlineKeyboardButton(text="Методика Сертори – 99 XTR", callback_data="buy_sertori")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])

def personal_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Программа 30 дней – 149 XTR", callback_data="buy_pers_30")],
        [InlineKeyboardButton(text="Программа на год – 499 XTR", callback_data="buy_pers_year")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("⚡ <b>АЛЬФА-МАССА</b> \n\n Выберите параметр:", reply_markup=main_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "category_basic")
async def basic_handler(callback: CallbackQuery):
    await callback.message.edit_text("🏋️ 🧬<b>Базовые протоколы</b> \n\n Выберите продукт:", reply_markup=basic_keyboard(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "category_personal")
async def personal_handler(callback: CallbackQuery):
    await callback.message.edit_text("🔥 <b>Персональные программы</b> \n\n Выберите продукт:", reply_markup=personal_keyboard(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "back_main")
async def back_handler(callback: CallbackQuery):
    await callback.message.edit_text("⚡ <b>АЛЬФА-МАССА</b> \n\n Выберите параметр:", reply_markup=main_keyboard(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def product_handler(callback: CallbackQuery):
    payload = callback.data.replace("buy_", "", 1)
    product = PRODUKTIB.get(payload, PRODUKTIB["сухой"])
    await callback.message.answer_invoice(
        title=product["title"], description=f"Оплата {product['title']}", payload=payload,
        currency="XTR", prices=[LabeledPrice(label=product["title"], amount=product["цена"])]
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_query_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message, bot: Bot):
    payload = message.successful_payment.invoice_payload
    product = PRODUKTIB.get(payload, PRODUKTIB["сухой"])
    try:
        channel_id = product.get("канал") or product.get("channel")
        invite = await bot.create_chat_invite_link(chat_id=channel_id, member_limit=1)
        await message.answer(f"✅ <b>Оплата получена!</b> \n\n 📦 <b>{product['title']}</b> \n\n Ссылка на канал: {invite.invite_link}", parse_mode="HTML")
    except Exception as e:
        await message.answer("Ошибка создания ссылки. Обратитесь к администратору.")

async def main():
    bot = Bot(token=BOT_TOKEN)
    print("⚡ Альфа-МАССА-БОТ запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
