from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from aiogram.filters import Command
import config
import database
import logging
import asyncio
from telegram_api import send_message

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = config.TOKEN
bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.setup_bot(bot)

# Создаем словарь для хранения состояния пользователей
user_states = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    commands = [
        '/start - Приветственное сообщение',
        '/help - Список доступных команд',
        '/burgers - Просмотр списка бургеров',
        '/cart - Просмотр корзины',
        '/remove_from_cart - Удалить бургер из корзины',
        '/admin_remove_burger - Удалить бургер из базы данных (только для администратора)'
    ]
    await message.reply(
        'Добро пожаловать в наш магазин бургеров!\n\nДоступные команды:\n' + '\n'.join(commands))

@dp.message(Command("help"))
async def help_command(message: types.Message):
    commands = [
        '/start - Приветственное сообщение',
        '/help - Список доступных команд',
        '/burgers - Просмотр списка бургеров',
        '/cart - Просмотр корзины',
        '/remove_from_cart - Удалить бургер из корзины',
        '/admin_remove_burger - Удалить бургер из базы данных (только для администратора)'
    ]
    await message.reply('Доступные команды:\n' + '\n'.join(commands))

@dp.message(Command("burgers"))
async def list_burgers(message: types.Message):
    burgers = await database.async_get_burgers()
    if not burgers:
        await message.reply('Бургеров пока нет.')
        return

    keyboard = []
    for burger in burgers:
        keyboard.append([InlineKeyboardButton(text=burger[1], callback_data=f'burger_{burger[0]}')])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.reply('Выберите бургер:', reply_markup=reply_markup)

@dp.callback_query(lambda c: c.data and c.data.startswith('burger_'))
async def burger_details(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    burger_id = int(callback_query.data.split('_')[1])
    burgers = await database.async_get_burgers()
    burger = next((b for b in burgers if b[0] == burger_id), None)

    if burger:
        text = f'{burger[1]}\n\n{burger[2]}\n\nЦена: {burger[3]}'
        user_id = callback_query.from_user.id
        if user_id not in user_states:
            user_states[user_id] = {}
        if 'quantity' not in user_states[user_id]:
            user_states[user_id]['quantity'] = 1
        quantity = user_states[user_id]['quantity']

        keyboard = [
            [
                InlineKeyboardButton(text='-', callback_data=f'decrease_{burger[0]}'),
                InlineKeyboardButton(text=str(quantity), callback_data=f'quantity_{burger[0]}'),
                InlineKeyboardButton(text='+', callback_data=f'increase_{burger[0]}')
            ],
            [InlineKeyboardButton(text='Добавить в корзину', callback_data=f'add_to_cart_{burger[0]}_{quantity}')]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await bot.edit_message_text(text=text, chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, reply_markup=reply_markup)

@dp.callback_query(lambda c: c.data and c.data.startswith('increase_'))
async def increase_quantity(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    burger_id = int(callback_query.data.split('_')[1])
    user_id = callback_query.from_user.id
    if user_id not in user_states:
        user_states[user_id] = {}
    if 'quantity' not in user_states[user_id]:
        user_states[user_id]['quantity'] = 1
    user_states[user_id]['quantity'] += 1
    quantity = user_states[user_id]['quantity']

    await update_quantity(callback_query, burger_id, quantity)

@dp.callback_query(lambda c: c.data and c.data.startswith('decrease_'))
async def decrease_quantity(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    burger_id = int(callback_query.data.split('_')[1])
    user_id = callback_query.from_user.id
    if user_id not in user_states:
        user_states[user_id] = {}
    if 'quantity' not in user_states[user_id]:
        user_states[user_id]['quantity'] = 1
    user_states[user_id]['quantity'] = max(1, user_states[user_id]['quantity'] - 1)
    quantity = user_states[user_id]['quantity']

    await update_quantity(callback_query, burger_id, quantity)

async def update_quantity(callback_query: types.CallbackQuery, burger_id: int, quantity: int):
    await bot.answer_callback_query(callback_query.id)

    burgers = await database.async_get_burgers()
    burger = next((b for b in burgers if b[0] == burger_id), None)

    if burger:
        text = f'{burger[1]}\n\n{burger[2]}\n\nЦена: {burger[3]}'
        keyboard = [
            [
                InlineKeyboardButton(text='-', callback_data=f'decrease_{burger[0]}'),
                InlineKeyboardButton(text=str(quantity), callback_data=f'quantity_{burger[0]}'),
                InlineKeyboardButton(text='+', callback_data=f'increase_{burger[0]}')
            ],
            [InlineKeyboardButton(text='Добавить в корзину', callback_data=f'add_to_cart_{burger[0]}_{quantity}')]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await bot.edit_message_text(text=text, chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, reply_markup=reply_markup)

@dp.callback_query(lambda c: c.data and c.data.startswith('add_to_cart_'))
async def add_to_cart(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    data_parts = callback_query.data.split('_')
    if len(data_parts) == 4 and data_parts[0] == 'add_to_cart' and data_parts[1].isdigit() and data_parts[2].isdigit():
        burger_id = int(data_parts[1])
        quantity = int(data_parts[2])
        user_id = callback_query.from_user.id
        database.add_to_cart(user_id, burger_id, quantity)

        message_text = f'Добавлено {quantity} бургеров в корзину!'
        if message_text:
            await send_message(user_id, message_text, TOKEN)
        else:
            await send_message(user_id, 'Произошла ошибка при добавлении бургеров в корзину.', TOKEN)

        commands = [
            '/start - Приветственное сообщение',
            '/help - Список доступных команд',
            '/burgers - Просмотр списка бургеров',
            '/cart - Просмотр корзины',
            '/remove_from_cart - Удалить бургер из корзины'
        ]
        await bot.send_message(callback_query.message.chat.id, 'Доступные команды:\n' + '\n'.join(commands))
    else:
        await bot.edit_message_text(text='Ошибка: неверный формат данных.', chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)

@dp.message(Command("cart"))
async def view_cart(message: types.Message):
    user_id = message.from_user.id
    cart_items = database.get_cart(user_id)
    if not cart_items:
        await message.reply('Ваша корзина пуста.')
        return

    cart_text = 'Ваша корзина:\n'
    total_price = 0
    burger_counts = {}
    for item in cart_items:
        burger_name = item[1]
        burger_price = item[3]
        quantity = item[4]
        if burger_name in burger_counts:
            burger_counts[burger_name]['quantity'] += quantity
        else:
            burger_counts[burger_name] = {'price': burger_price, 'quantity': quantity}

    for burger_name, data in burger_counts.items():
        cart_text += f'{burger_name} - {data["price"]} руб. (Количество: {data["quantity"]})\n'
        total_price += data["price"] * data["quantity"]

    cart_text += f'\nИтого: {total_price} руб.'

    # Добавление кнопки "Купить"
    keyboard = [[InlineKeyboardButton(text='Купить', callback_data='buy')]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await message.reply(cart_text, reply_markup=reply_markup)

@dp.message(Command("remove_from_cart"))
async def remove_from_cart(message: types.Message):
    user_id = message.from_user.id
    cart_items = database.get_cart(user_id)
    if not cart_items:
        await message.reply('Ваша корзина пуста.')
        return

    burger_counts = {}
    for item in cart_items:
        burger_id = item[0]
        burger_name = item[1]
        quantity = item[4]
        if burger_id in burger_counts:
            burger_counts[burger_id]['quantity'] += quantity
        else:
            burger_counts[burger_id] = {'name': burger_name, 'quantity': quantity}

    keyboard = []
    for burger_id, data in burger_counts.items():
        keyboard.append([InlineKeyboardButton(text=f'Удалить {data["name"]} (Количество: {data["quantity"]})',
                                              callback_data=f'remove_from_cart_{burger_id}')])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.reply('Выберите бургер для удаления:', reply_markup=reply_markup)

@dp.callback_query(lambda c: c.data and c.data.startswith('remove_from_cart_'))
async def confirm_remove_from_cart(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    data_parts = callback_query.data.split('_')
    if len(data_parts) == 4 and data_parts[0] == 'remove' and data_parts[1] == 'from' and data_parts[2] == 'cart' and \
            data_parts[3].isdigit():
        burger_id = int(data_parts[3])
        user_id = callback_query.from_user.id
        cart_items = database.get_cart(user_id)
        burger = next((b for b in cart_items if b[0] == burger_id), None)

        if burger:
            quantity = burger[4]
            await bot.edit_message_text(
                text=f'Сколько бургеров {burger[1]} вы хотите удалить? (Максимум: {quantity})',
                chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
            user_states[user_id]['remove_burger_id'] = burger_id
            user_states[user_id]['remove_quantity'] = quantity
        else:
            await bot.edit_message_text(text='Бургер не найден в корзине.', chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    else:
        await bot.edit_message_text(text='Ошибка: неверный формат данных.', chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)

@dp.message(lambda message: message.text.isdigit())
async def handle_remove_quantity(message: types.Message):
    user_input = message.text
    try:
        quantity_to_remove = int(user_input)
        user_id = message.from_user.id
        burger_id = user_states[user_id].get('remove_burger_id')
        max_quantity = user_states[user_id].get('remove_quantity')

        if max_quantity is None:
            await message.reply('Ошибка: невозможно определить максимальное количество для удаления.')
            return

        if quantity_to_remove > 0 and quantity_to_remove <= max_quantity:
            database.remove_from_cart(user_id, burger_id, quantity_to_remove)
            await message.reply(f'Удалено {quantity_to_remove} бургеров.')

            # Отправка сообщения с доступными командами
            commands = [
                '/start - Приветственное сообщение',
                '/help - Список доступных команд',
                '/burgers - Просмотр списка бургеров',
                '/cart - Просмотр корзины',
                '/remove_from_cart - Удалить бургер из корзины'
            ]
            await message.reply('Доступные команды:\n' + '\n'.join(commands))
        else:
            await message.reply(f'Введите число от 1 до {max_quantity}.')
    except ValueError:
        await message.reply('Пожалуйста, введите число.')

@dp.callback_query(lambda c: c.data and c.data == 'buy')
async def buy(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    user_id = callback_query.from_user.id
    cart_items = database.get_cart(user_id)
    if not cart_items:
        await bot.edit_message_text('Ваша корзина пуста.', chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        return

    await send_invoice(callback_query)

async def send_invoice(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    user_id = callback_query.from_user.id
    cart_items = database.get_cart(user_id)
    if not cart_items:
        await bot.edit_message_text('Ваша корзина пуста.', chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        return

    # Здесь можно добавить логику для расчета итоговой цены с учетом доставки
    total_price = calculate_total_price(cart_items)

    # Дополнительная проверка и логирование
    if not isinstance(total_price, int):
        logger.error(f"Total price is not an integer: {total_price}")
        await bot.edit_message_text('Ошибка при расчете стоимости заказа. Пожалуйста, попробуйте позже.', chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        return

    await bot.send_invoice(
        chat_id=callback_query.message.chat.id,
        title='Оплата заказа',
        description='Оплата заказа в нашем магазине',
        provider_token=config.PAYMENTS_PROVIDER_TOKEN,
        currency='rub',
        prices=[LabeledPrice(label='Итого', amount=total_price)],
        need_name=True,
        need_phone_number=True,
        need_email=True,
        need_shipping_address=True,
        is_flexible=True,
        start_parameter='example',
        payload='some-invoice-payload'
    )

def calculate_total_price(cart_items):
    total_price = 0
    for item in cart_items:
        total_price += item[3] * item[4] * 100  # item[3] - цена в рублях, item[4] - количество
    return int(total_price)

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda message: message.successful_payment)
async def process_successful_payment(message: types.Message):
    print('Successful Payment')
    payment_info = message.successful_payment.to_dict()
    print(payment_info)

    await message.reply('Спасибо за покупку! Ваш заказ оформлен.')

@dp.message(Command("admin_remove_burger"))
async def admin_remove_burger(message: types.Message):
    user_id = message.from_user.id
    if user_id != config.ADMIN_USER_ID:
        await message.reply('У вас нет прав для выполнения этой команды.')
        return

    await message.reply('Пожалуйста, укажите id бургера, который вы хотите удалить.')
    user_states[user_id]['state'] = 'awaiting_burger_id'

@dp.message(lambda message: user_states.get(message.from_user.id, {}).get('state') == 'awaiting_burger_id')
async def handle_burger_id(message: types.Message):
    user_id = message.from_user.id
    if user_id != config.ADMIN_USER_ID:
        await message.reply('У вас нет прав для выполнения этой команды.')
        return

    user_input = message.text
    try:
        burger_id = int(user_input)
        await database.async_remove_burger(burger_id)
        await message.reply(f'Бургер с id {burger_id} успешно удален.')
        await list_burgers(message)  # После удаления бургера, обновляем список бургеров
    except ValueError:
        await message.reply('Пожалуйста, введите корректный id бургера.')

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    database.init_db()
    asyncio.run(main())