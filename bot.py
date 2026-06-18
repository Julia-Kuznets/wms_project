import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ВСТАВЬ СЮДА СВОЙ ТОКЕН ОТ BOTFATHER
BOT_TOKEN = "8430082338:AAFHcc9nUynuPrBOdmuseoTFR1CDCCvOceY"

# URL нашего локального Django API
API_URL = "http://127.0.0.1:8000/api/v1/tasks"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 1. Приветствие
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! Я бот диспетчерской службы ООО «Премакса».\n"
        f"Твой Telegram ID: {message.from_user.id}. Ожидай поступления новых заявок."
    )

# 2. Эмуляция прихода заявки (Специальная команда для тестирования и скриншотов)
# 2. Получение списка РЕАЛЬНЫХ новых заявок из базы Django
@dp.message(Command("tasks"))
async def cmd_show_tasks(message: types.Message):
    # Для запросов к нашему локальному Django прокси не нужен, 
    # поэтому создаем чистую сессию
    async with aiohttp.ClientSession() as session:
        # API_URL у нас = "http://127.0.0.1:8000/api/v1/tasks" (мы добавили этот путь)
        url = f"{API_URL}/" 
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    tasks = await response.json()
                    
                    # Фильтруем только новые заявки (которые еще никто не взял)
                    new_tasks =[t for t in tasks if t['status'] == 'NEW']
                    
                    if not new_tasks:
                        await message.answer("✅ В данный момент новых свободных заявок нет.")
                        return
                        
                    # Если заявки есть, выводим каждую отдельным сообщением с кнопкой
                    await message.answer(f"Найдено доступных заявок: {len(new_tasks)}")
                    
                    for task in new_tasks:
                        task_id = task['id']
                        machine_id = task['machine'] # ID автомата из БД
                        
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 Принять заявку в работу", callback_data=f"take_{task_id}")]
                        ])
                        
                        await message.answer(
                            f"🚨 <b>НОВАЯ ЗАЯВКА #{task_id}</b>\n\n"
                            f"<b>ID Автомата:</b> {machine_id}\n"
                            f"<b>Дата создания:</b> {task['created_at'][:10]}\n\n"
                            f"<i>Нажми кнопку ниже, чтобы закрепить задачу за собой.</i>",
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                else:
                    await message.answer(f"⚠️ Ошибка сервера. Код: {response.status}")
        except Exception as e:
            await message.answer(f"Ошибка соединения с API Django: {e}")


# 3. Тот самый обработчик кнопки (Логика из Листинга 3.3)
@dp.callback_query(F.data.startswith("take_"))
async def take_task_callback(callback_query: types.CallbackQuery):
    # Вытаскиваем ID заявки из callback_data (например, take_1 -> 1)
    task_id = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id
    
    # Отправляем POST запрос к нашему Django API
    async with aiohttp.ClientSession() as session:
        url = f"{API_URL}/{task_id}/assign/"
        payload = {"user_id": user_id}
        
        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    # Выдаем кнопку для завершения
                    finish_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Завершить работу", callback_data=f"done_{task_id}")]
                    ])
                    await callback_query.message.edit_text(
                        f"✅ <b>Заявка #{task_id} успешно принята!</b>\nВыезжайте на объект.",
                        reply_markup=finish_kb,
                        parse_mode="HTML"
                    )

                elif response.status == 400:
                    data = await response.json()
                    await callback_query.message.edit_text(
                        f"❌ <b>Ошибка:</b> {data.get('error', 'Уже занято')}",
                        parse_mode="HTML"
                    )
                elif response.status == 404:
                    await callback_query.message.edit_text("⚠️ Заявка не найдена в базе данных.")
                else:
                    await callback_query.message.edit_text("⚠️ Ошибка сервера.")
        except Exception as e:
            await callback_query.answer(f"Ошибка соединения с сервером API: {e}", show_alert=True)
# 4. Обработчик кнопки ЗАВЕРШЕНИЯ РАБОТЫ
# 4. Обработчик кнопки ЗАВЕРШЕНИЯ РАБОТЫ
@dp.callback_query(F.data.startswith("done_"))
async def done_task_callback(callback_query: types.CallbackQuery):
    task_id = callback_query.data.split('_')[1]
    
    # ЧИСТАЯ СЕССИЯ БЕЗ ВСЯКИХ КОННЕКТОРОВ И ПРОКСИ
    async with aiohttp.ClientSession() as session: 
        url = f"{API_URL}/{task_id}/complete/"
        
        try:
            async with session.post(url, json={"user_id": callback_query.from_user.id}) as response:
                if response.status == 200:
                    await callback_query.message.edit_text(
                        f"🏁 <b>Заявка #{task_id} выполнена!</b>\nОстатки автомата восполнены до 100%.",
                        parse_mode="HTML"
                    )
                elif response.status == 400:
                    data = await response.json()
                    await callback_query.message.edit_text(f"❌ Ошибка: {data.get('error')}")
                else:
                    await callback_query.message.edit_text("⚠️ Ошибка при завершении заявки.")
        except Exception as e:
            await callback_query.answer(f"Ошибка API: {e}", show_alert=True)


async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
