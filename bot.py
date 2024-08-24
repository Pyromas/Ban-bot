# bot.py

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from config import API_TOKEN
import logic

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Инициализация базы данных при запуске
logic.init_db()

# Добавление ссылки в черный список
@dp.message_handler(commands=['addlink'])
async def add_link(message: types.Message):
    if message.from_user.id not in [admin.user.id for admin in await bot.get_chat_administrators(message.chat.id)]:
        await message.reply("У вас нет прав для выполнения этой команды.")
        return

    link = message.get_args()
    logic.add_link(link, message.from_user.username, message.date)
    await message.reply(f'Ссылка {link} добавлена в черный список.')

# Хендлер на проверку всех сообщений
@dp.message_handler()
async def check_message(message: types.Message):
    blocked_link = logic.check_message_for_links(message.text)
    if blocked_link:
        await message.delete()
        warning_count = logic.add_warning(message.from_user.id, message.chat.id)

        await message.reply(f'{message.from_user.first_name}, эта ссылка запрещена! У вас {warning_count}/3 предупреждений.')

        if warning_count >= 3:
            await message.chat.kick(user_id=message.from_user.id)
            await message.reply(f'{message.from_user.first_name} был забанен за нарушение правил.')

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
