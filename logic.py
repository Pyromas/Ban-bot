import sqlite3
from config import DB_NAME

# Подключение к базе данных
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Инициализация базы данных
def init_db():
    cursor.execute('''CREATE TABLE IF NOT EXISTS blocked_links (
                      id INTEGER PRIMARY KEY, 
                      link TEXT UNIQUE, 
                      added_by TEXT, 
                      date_added TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_warnings (
                      id INTEGER PRIMARY KEY, 
                      user_id INTEGER, 
                      chat_id INTEGER, 
                      warning_count INTEGER DEFAULT 0)''')
    conn.commit()

# Добавление ссылки в черный список
def add_link(link, added_by, date_added):
    cursor.execute('INSERT OR IGNORE INTO blocked_links (link, added_by, date_added) VALUES (?, ?, ?)', 
                   (link, added_by, date_added))
    conn.commit()

# Проверка сообщения на наличие заблокированных ссылок
def check_message_for_links(message_text):
    cursor.execute('SELECT link FROM blocked_links')
    links = cursor.fetchall()

    for link in links:
        if link[0] in message_text:
            return link[0]
    return None

# Получение количества варнов пользователя
def get_warning_count(user_id, chat_id):
    cursor.execute('SELECT warning_count FROM user_warnings WHERE user_id = ? AND chat_id = ?', 
                   (user_id, chat_id))
    result = cursor.fetchone()
    return result[0] if result else 0

# Добавление варна пользователю
def add_warning(user_id, chat_id):
    warning_count = get_warning_count(user_id, chat_id) + 1
    if warning_count > 1:
        cursor.execute('UPDATE user_warnings SET warning_count = ? WHERE user_id = ? AND chat_id = ?', 
                       (warning_count, user_id, chat_id))
    else:
        cursor.execute('INSERT INTO user_warnings (user_id, chat_id, warning_count) VALUES (?, ?, ?)', 
                       (user_id, chat_id, warning_count))
    conn.commit()
    return warning_count
3. bot.py
Этот файл будет содержать основной код для работы с Telegram API, обработку команд и сообщений. Здесь будут импортироваться функции из logic.py.

python
Копировать код
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
