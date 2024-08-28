import asyncio
import atexit
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from aiogram.filters import Command
import config
import database
import logging
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = config.TOKEN
bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.setup_bot(bot)

commands = [
    '/start - Приветственное сообщение',
    '/help - Список доступных команд',
    '/burgers - Просмотр списка бургеров',
    '/cart - Просмотр корзины'
]


@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    state = await database.async_get_user_state(user_id)
    if state:
        await message.reply(f'Добро пожаловать обратно! Последний раз вы были: {state}')
    else:
        await message.reply('Добро пожаловать в наш магазин бургеров!')
    await database.async_save_user_state(user_id, 'start')
    await message.reply('Доступные команды:\n' + '\n'.join(commands))


@dp.message(Command("help"))
async def help_command(message: types.Message):
    user_id = message.from_user.id
    await database.async_save_user_state(user_id, 'help')
    await message.reply('Доступные команды:\n' + '\n'.join(commands))


@dp.message(Command("burgers"))
async def list_burgers(message: types.Message):
    user_id = message.from_user.id
    await database.async_save_user_state(user_id, 'burgers')
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
        await database.async_save_user_state(user_id, f'awaiting_quantity_{burger_id}_1')

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text='-', callback_data=f'decrease_{burger_id}'),
            InlineKeyboardButton(text='1', callback_data=f'quantity_{burger_id}_1'),
            InlineKeyboardButton(text='+', callback_data=f'increase_{burger_id}')
        )
        builder.row(
            InlineKeyboardButton(text='Добавить в корзину', callback_data=f'add_to_cart_{burger_id}')
        )

        await bot.send_message(callback_query.message.chat.id, f'{text}\n\nВыберите количество бургеров:',
                               reply_markup=builder.as_markup())
    else:
        await bot.send_message(callback_query.message.chat.id, 'Бургер не найден.')


@dp.callback_query(lambda c: c.data and c.data.startswith('increase_'))
async def increase_quantity(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    burger_id = int(callback_query.data.split('_')[1])
    user_id = callback_query.from_user.id
    state = await database.async_get_user_state(user_id)

    if state and state.startswith('awaiting_quantity_'):
        current_quantity = int(state.split('_')[3])
        new_quantity = current_quantity + 1
        await database.async_save_user_state(user_id, f'awaiting_quantity_{burger_id}_{new_quantity}')

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text='-', callback_data=f'decrease_{burger_id}'),
            InlineKeyboardButton(text=str(new_quantity), callback_data=f'quantity_{burger_id}_{new_quantity}'),
            InlineKeyboardButton(text='+', callback_data=f'increase_{burger_id}')
        )
        builder.row(
            InlineKeyboardButton(text='Добавить в корзину', callback_data=f'add_to_cart_{burger_id}')
        )

        await bot.edit_message_reply_markup(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=builder.as_markup()
        )


@dp.callback_query(lambda c: c.data and c.data.startswith('decrease_'))
async def decrease_quantity(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    burger_id = int(callback_query.data.split('_')[1])
    user_id = callback_query.from_user.id
    state = await database.async_get_user_state(user_id)

    if state and state.startswith('awaiting_quantity_'):
        current_quantity = int(state.split('_')[3])
        new_quantity = max(current_quantity - 1, 1)
        await database.async_save_user_state(user_id, f'awaiting_quantity_{burger_id}_{new_quantity}')

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text='-', callback_data=f'decrease_{burger_id}'),
            InlineKeyboardButton(text=str(new_quantity), callback_data=f'quantity_{burger_id}_{new_quantity}'),
            InlineKeyboardButton(text='+', callback_data=f'increase_{burger_id}')
        )
        builder.row(
            InlineKeyboardButton(text='Добавить в корзину', callback_data=f'add_to_cart_{burger_id}')
        )

        await bot.edit_message_reply_markup(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=builder.as_markup()
        )


@dp.callback_query(lambda c: c.data and c.data.startswith('add_to_cart_'))
async def add_to_cart(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    data_parts = callback_query.data.split('_')
    print(f"Callback data: {callback_query.data}")  # Добавлено для отладки

    if len(data_parts) < 4:
        await bot.send_message(callback_query.message.chat.id, 'Ошибка: некорректные данные.')
        return

    try:
        burger_id = int(data_parts[3])
    except ValueError:
        await bot.send_message(callback_query.message.chat.id, 'Ошибка: некорректный идентификатор бургера.')
        return

    user_id = callback_query.from_user.id
    state = await database.async_get_user_state(user_id)

    if state and state.startswith('awaiting_quantity_'):
        try:
            quantity = int(state.split('_')[3])
        except ValueError:
            await bot.send_message(callback_query.message.chat.id, 'Ошибка: некорректное количество бургеров.')
            return

        await database.async_add_to_cart(user_id, burger_id, quantity)
        await bot.send_message(callback_query.message.chat.id, f'Добавлено {quantity} бургеров в корзину!')
        await database.async_save_user_state(user_id, 'start')
        await bot.send_message(callback_query.message.chat.id, 'Доступные команды:\n' + '\n'.join(commands))


@dp.message(lambda message: message.text.isdigit())
async def handle_quantity_input(message: types.Message):
    user_id = message.from_user.id
    user_state = await database.async_get_user_state(user_id)

    if user_state and user_state.startswith('awaiting_quantity_'):
        burger_id = int(user_state.split('_')[2])
        quantity = int(message.text)

        if quantity > 0:
            try:
                await database.async_add_to_cart(user_id, burger_id, quantity)
                await message.reply(f'Добавлено {quantity} бургеров в корзину!')
                await message.reply('Доступные команды:\n' + '\n'.join(commands))
            except Exception as e:
                print(f"Error adding to cart: {e}")
                await message.reply('Произошла ошибка при добавлении бургеров в корзину.')

            await database.async_save_user_state(user_id, 'start')
        else:
            await message.reply('Количество должно быть больше нуля.')
    else:
        await message.reply('Неожиданный ввод. Пожалуйста, используйте команды бота.')


@dp.message(Command("cart"))
async def view_cart(message: types.Message):
    user_id = message.from_user.id
    await database.async_save_user_state(user_id, 'cart')
    cart_items = await database.async_get_cart(user_id)
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
            burger_counts[burger_name] = {'price': burger_price, 'quantity': quantity, 'id': item[0]}

    keyboard = []
    for burger_name, data in burger_counts.items():
        cart_text += f'{burger_name} - {data["price"]} руб. (Количество: {data["quantity"]})\n'
        total_price += data["price"] * data["quantity"]
        keyboard.append([InlineKeyboardButton(text=f'Удалить {burger_name}', callback_data=f'delete_{data["id"]}')])

    cart_text += f'\nИтого: {total_price} руб.'

   
    keyboard.append([InlineKeyboardButton(text='Купить', callback_data='buy')])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.reply(cart_text, reply_markup=reply_markup)


@dp.callback_query(lambda c: c.data and c.data == 'buy')
async def buy(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    user_id = callback_query.from_user.id
    cart_items = await database.async_get_cart(user_id)
    if not cart_items:
        await bot.edit_message_text('Ваша корзина пуста.', chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id)
        return

    await send_invoice(callback_query)


async def send_invoice(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    user_id = callback_query.from_user.id
    cart_items = await database.async_get_cart(user_id)
    if not cart_items:
        await bot.edit_message_text('Ваша корзина пуста.', chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id)
        return

    total_price = await calculate_total_price(cart_items)
    logging.info("Sending invoice to user")
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
    logging.info("Invoice sent successfully")


async def calculate_total_price(cart_items):
    total_price = 0
    for item in cart_items:
        total_price += item[3] * item[4] * 100  # item[3] - цена в рублях, item[4] - количество
    return int(total_price)


@dp.callback_query(lambda c: c.data and c.data.startswith('delete_'))
async def delete_burger(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    data_parts = callback_query.data.split('_')
    if len(data_parts) == 2 and data_parts[0] == 'delete' and data_parts[1].isdigit():
        burger_id = int(data_parts[1])
        user_id = callback_query.from_user.id
        cart_items = await database.async_get_cart(user_id)
        burger = next((b for b in cart_items if b[0] == burger_id), None)

        if burger:
            quantity = burger[4]
            builder = InlineKeyboardBuilder()
            for i in range(1, quantity + 1):
                builder.add(InlineKeyboardButton(text=str(i), callback_data=f'remove_{burger_id}_{i}'))
            builder.adjust(3)  

            await bot.send_message(
                chat_id=callback_query.message.chat.id,
                text=f'Сколько бургеров {burger[1]} вы хотите удалить?',
                reply_markup=builder.as_markup()
            )
        else:
            await bot.send_message(
                chat_id=callback_query.message.chat.id,
                text='Бургер не найден в корзине.'
            )
    else:
        await bot.send_message(
            chat_id=callback_query.message.chat.id,
            text='Ошибка: неверный формат данных.'
        )


@dp.callback_query(lambda c: c.data and c.data.startswith('remove_'))
async def remove_burger(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    data_parts = callback_query.data.split('_')
    if len(data_parts) == 3 and data_parts[0] == 'remove' and data_parts[1].isdigit() and data_parts[2].isdigit():
        burger_id = int(data_parts[1])
        quantity_to_remove = int(data_parts[2])
        user_id = callback_query.from_user.id
        cart_items = await database.async_get_cart(user_id)
        burger = next((b for b in cart_items if b[0] == burger_id), None)

        if burger:
            quantity = burger[4]
            if 0 < quantity_to_remove <= quantity:
                await database.async_remove_from_cart(user_id, burger_id, quantity_to_remove)
                await bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text=f'Удалено {quantity_to_remove} бургеров {burger[1]}.'
                )
                await bot.send_message(callback_query.message.chat.id, 'Доступные команды:\n' + '\n'.join(commands))
            else:
                await bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text='Неверное количество бургеров для удаления.'
                )
        else:
            await bot.send_message(
                chat_id=callback_query.message.chat.id,
                text='Бургер не найден в корзине.'
            )
    else:
        await bot.send_message(
            chat_id=callback_query.message.chat.id,
            text='Ошибка: неверный формат данных.'
        )


async def main():
    await dp.start_polling(bot)


async def shutdown():
    await bot.close()
    await asyncio.sleep(0.1)


def atexit_handler():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(shutdown())


if __name__ == '__main__':
    database.init_db()
    atexit.register(atexit_handler)
    asyncio.run(main())
