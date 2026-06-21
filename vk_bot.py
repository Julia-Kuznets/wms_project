import os
import asyncio
import aiohttp
from vkbottle.bot import Bot, Message, MessageEvent
from vkbottle import Keyboard, Callback, GroupTypes
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.environ.get("VK_TOKEN")
# В докере Django будет доступен по имени контейнера 'web'
API_URL = os.environ.get("API_URL", "http://web:8000/api/v1/tasks")

if not VK_TOKEN:
    raise ValueError("VK_TOKEN не найден в переменных окружения!")

bot = Bot(token=VK_TOKEN)

# 1. Приветствие и регистрация
@bot.on.private_message(text=["/start", "Начать", "Привет"])
async def start_handler(message: Message):
    user_id = message.from_id
    await message.answer(
        f"Привет, {message.from_id}! Я бот технической поддержки ООО «Премакса».\n"
        f"Твой уникальный идентификатор зарегистрирован в системе.\n"
        f"Используй команду /tasks для просмотра активных заявок."
    )

# 2. Получение списка свободных задач
@bot.on.private_message(text="/tasks")
async def show_tasks_handler(message: Message):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_URL}/") as response:
                if response.status == 200:
                    tasks = await response.json()
                    new_tasks = [t for t in tasks if t['status'] == 'NEW']
                    
                    if not new_tasks:
                        await message.answer("✅ В данный момент свободных заявок нет.")
                        return
                    
                    for task in new_tasks:
                        task_id = task['id']
                        machine_id = task['machine']
                        desc = task.get('description', 'Требуется обслуживание')
                        
                        # Инлайновая клавиатура для ВКонтакте
                        keyboard = (
                            Keyboard(inline=True)
                            .add(Callback("🛠 Принять в работу", payload={"cmd": "take", "task_id": task_id}))
                        ).get_json()
                        
                        await message.answer(
                            f"🚨 <b>НОВАЯ ЗАЯВКА #{task_id}</b>\n\n"
                            f"<b>ID Автомата:</b> {machine_id}\n"
                            f"<b>Описание:</b> {desc}\n\n"
                            f"<i>Нажмите кнопку ниже для принятия задачи.</i>",
                            keyboard=keyboard
                        )
                else:
                    await message.answer("⚠️ Ошибка получения данных от сервера API.")
        except Exception as e:
            await message.answer(f"Ошибка соединения с API: {e}")

# 3. Обработка кликов по кнопкам (Callback-события в ВК)
@bot.on.raw_event(GroupTypes.MESSAGE_EVENT, dataclass=MessageEvent)
async def handle_callback(event: MessageEvent):
    payload = event.payload
    task_id = payload.get("task_id")
    
    # Формируем имя пользователя с префиксом vk_ для базы данных
    vk_username = f"vk_{event.user_id}"

    if payload.get("cmd") == "take":
        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/{task_id}/assign/"
            try:
                async with session.post(url, json={"user_id": vk_username}) as response:
                    if response.status == 200:
                        # Создаем клавиатуру с кнопкой завершения
                        keyboard = (
                            Keyboard(inline=True)
                            .add(Callback("✅ Завершить работу", payload={"cmd": "done", "task_id": task_id}))
                        ).get_json()
                        
                        # Редактируем сообщение в ВК
                        await bot.api.messages.edit(
                            peer_id=event.peer_id,
                            conversation_message_id=event.conversation_message_id,
                            message=f"✅ Заявка #{task_id} успешно принята! Выезжайте на объект.",
                            keyboard=keyboard
                        )
                    else:
                        await event.show_snackbar("❌ Заявку уже взял другой сотрудник.")
            except Exception as e:
                await event.show_snackbar(f"Ошибка API: {e}")

    elif payload.get("cmd") == "done":
        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/{task_id}/complete/"
            try:
                async with session.post(url, json={"user_id": vk_username}) as response:
                    if response.status == 200:
                        await bot.api.messages.edit(
                            peer_id=event.peer_id,
                            conversation_message_id=event.conversation_message_id,
                            message=f"🏁 Заявка #{task_id} выполнена! Остатки автомата восполнены до 100%."
                        )
                    else:
                        await event.show_snackbar("⚠️ Ошибка при завершении задачи.")
            except Exception as e:
                await event.show_snackbar(f"Ошибка API: {e}")

if __name__ == "__main__":
    bot.run_forever()