import json
import logging
import aiohttp
import os
from dotenv import load_dotenv

from vkbottle import Bot, Keyboard, Callback, KeyboardButtonColor, EMPTY_KEYBOARD
from vkbottle.dispatch.rules.base import CommandRule, ABCRule


class _DedupRule(ABCRule):
    def __init__(self):
        self._seen = set()

    async def check(self, event, **context) -> bool:
        msg_id = event.id
        if msg_id in self._seen:
            return False
        self._seen.add(msg_id)
        if len(self._seen) > 500:
            self._seen.clear()
        return True

load_dotenv()

VK_TOKEN = os.environ.get("VK_TOKEN")
if not VK_TOKEN:
    raise ValueError("VK_TOKEN не найден в переменных окружения или .env файле!")

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000/api/v1/tasks")

bot = Bot(token=VK_TOKEN)

bot.on.auto_rules.append(_DedupRule())


async def show_snackbar(event: dict, text: str):
    obj = event.get("object", {})
    await bot.api.messages.send_message_event_answer(
        event_id=obj["event_id"],
        user_id=obj["user_id"],
        peer_id=obj["peer_id"],
        event_data=json.dumps({"type": "show_snackbar", "text": text}),
    )


@bot.on.message(CommandRule("start"))
async def cmd_start(message):
    user_info = await bot.api.users.get(user_ids=[message.from_id])
    first_name = user_info[0].first_name if user_info else "пользователь"

    await message.answer(
        f"Привет, {first_name}! Я бот диспетчерской службы ООО «Премакса».\n"
        f"Твой VK ID: {message.from_id}. Ожидай поступления новых заявок."
    )


@bot.on.message(CommandRule("tasks"))
async def cmd_show_tasks(message):
    async with aiohttp.ClientSession() as session:
        url = f"{API_URL}/"

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    tasks = await response.json()

                    new_tasks = [t for t in tasks if t["status"] == "NEW"]

                    if not new_tasks:
                        await message.answer("✅ В данный момент новых свободных заявок нет.")
                        return

                    await message.answer(f"Найдено доступных заявок: {len(new_tasks)}")

                    for task in new_tasks:
                        task_id = task["id"]
                        machine_id = task["machine"]

                        keyboard = Keyboard(one_time=False, inline=True)
                        keyboard.add(
                            Callback(label="🛠 Принять заявку в работу", payload={"type": "take", "task_id": task_id}),
                            color=KeyboardButtonColor.PRIMARY,
                        )

                        await message.answer(
                            f"🚨 НОВАЯ ЗАЯВКА #{task_id}\n\n"
                            f"ID Автомата: {machine_id}\n"
                            f"Дата создания: {task['created_at'][:10]}\n\n"
                            f"Нажми кнопку ниже, чтобы закрепить задачу за собой.",
                            keyboard=str(keyboard),
                        )
                else:
                    await message.answer(f"⚠️ Ошибка сервера. Код: {response.status}")
        except Exception as e:
            await message.answer(f"Ошибка соединения с API Django: {e}")


@bot.on.raw_event("message_event", dataclass=dict)
async def handle_button(event: dict):
    obj = event.get("object")
    if not obj:
        return

    raw_payload = obj.get("payload")
    if isinstance(raw_payload, str):
        payload = json.loads(raw_payload)
    else:
        payload = raw_payload or {}

    action_type = payload.get("type")
    task_id = payload.get("task_id")

    user_id = obj["user_id"]

    async def ack():
        await bot.api.messages.send_message_event_answer(
            event_id=obj["event_id"],
            user_id=obj["user_id"],
            peer_id=obj["peer_id"],
            event_data="",
        )

    if not task_id:
        await ack()
        return

    if action_type == "take":
        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/{task_id}/assign/"
            payload_data = {"user_id": user_id}

            try:
                async with session.post(url, json=payload_data) as response:
                    if response.status == 200:
                        await ack()
                        finish_kb = Keyboard(one_time=False, inline=True)
                        finish_kb.add(
                            Callback(label="✅ Завершить работу", payload={"type": "done", "task_id": task_id}),
                            color=KeyboardButtonColor.POSITIVE,
                        )

                        await bot.api.messages.edit(
                            peer_id=obj["peer_id"],
                            cmid=obj["conversation_message_id"],
                            message=f"✅ Заявка #{task_id} успешно принята!\nВыезжайте на объект.",
                            keyboard=str(finish_kb),
                        )
                    elif response.status == 400:
                        data = await response.json()
                        error_text = data.get("error", "Уже занято")
                        await show_snackbar(event, f"❌ {error_text}")
                    elif response.status == 404:
                        await show_snackbar(event, "⚠️ Заявка не найдена в базе данных.")
                    else:
                        await show_snackbar(event, "⚠️ Ошибка сервера.")
            except Exception as e:
                await show_snackbar(event, f"Ошибка соединения: {e}")

    elif action_type == "done":
        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/{task_id}/complete/"

            try:
                async with session.post(url, json={"user_id": user_id}) as response:
                    if response.status == 200:
                        await ack()
                        await bot.api.messages.edit(
                            peer_id=obj["peer_id"],
                            cmid=obj["conversation_message_id"],
                            message=f"🏁 Заявка #{task_id} выполнена!\nОстатки автомата восполнены до 100%.",
                            keyboard=EMPTY_KEYBOARD,
                        )
                    elif response.status == 400:
                        data = await response.json()
                        await show_snackbar(event, f"❌ {data.get('error')}")
                    else:
                        await show_snackbar(event, "⚠️ Ошибка при завершении заявки.")
            except Exception as e:
                await show_snackbar(event, f"Ошибка API: {e}")
    else:
        await ack()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("VK бот запущен...")
    bot.run()
