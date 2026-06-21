import os
import random
import redis as _redis
import requests
from celery import shared_task
from django.contrib.auth import get_user_model
from .models import MachineSlot, ServiceTask

User = get_user_model()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
VK_TOKEN = os.environ.get("VK_TOKEN")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

try:
    _redis_client = _redis.from_url(REDIS_URL, decode_responses=True)
    _redis_client.ping()
except Exception:
    _redis_client = None

VK_SUBSCRIBERS_KEY = "vk_bot:subscribers"
VK_API_VERSION = "5.199"


def broadcast_vk_message(task_id, machine_id, description):
    if not VK_TOKEN or not _redis_client:
        return

    subscriber_ids = list(_redis_client.smembers(VK_SUBSCRIBERS_KEY))
    if not subscriber_ids:
        return

    text = (
        f"⚠ АВТОМАТИЧЕСКАЯ ЗАЯВКА #{task_id}\n\n"
        f"Автомат: ID {machine_id}\n"
        f"Проблема: {description}\n\n"
        f"Зайди в меню /tasks, чтобы взять в работу!"
    )

    for uid in subscriber_ids:
        url = "https://api.vk.com/method/messages.send"
        params = {
            "access_token": VK_TOKEN,
            "v": VK_API_VERSION,
            "user_id": uid,
            "message": text,
            "random_id": 0,
        }
        try:
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
            if "error" in data:
                code = data["error"].get("error_code")
                if code == 901:
                    _redis_client.srem(VK_SUBSCRIBERS_KEY, uid)
        except Exception as e:
            print(f"Ошибка отправки VK-уведомления пользователю {uid}: {e}")


def broadcast_telegram_message(task_id, machine_id, description):
    """
    Отправляет push-уведомление всем техникам (Broadcasting).
    Для MVP мы рассылаем сообщение всем пользователям, 
    чьи имена (username) состоят только из цифр (это Telegram ID).
    """
    if not BOT_TOKEN:
        return

    # Ищем техников (тех, кто хоть раз нажимал кнопку в боте и создался в БД)
    technicians = User.objects.filter(username__iregex=r'^\d+$')
    
    text = (
        f"🚨 <b>АВТОМАТИЧЕСКАЯ ЗАЯВКА #{task_id}</b>\n\n"
        f"<b>Автомат:</b> ID {machine_id}\n"
        f"<b>Проблема:</b> {description}\n\n"
        f"<i>Зайди в меню /tasks, чтобы взять в работу!</i>"
    )
    
    for tech in technicians:
        chat_id = tech.username
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            # Делаем синхронный POST-запрос к API Телеграма
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"Ошибка отправки Push-уведомления: {e}")

@shared_task
def emulate_sales_and_check_stock():
    """
    Эмулятор продаж и предиктивный алгоритм расчета остатков.
    Запускается по расписанию (Celery Beat).
    """
    print("Запуск эмулятора продаж...")
    slots = MachineSlot.objects.all()
    
    for slot in slots:
        # 1. Эмуляция продаж: случайно списываем от 0 до 2 единиц товара
        sold = random.randint(0, 2)
        if slot.current_quantity >= sold:
            slot.current_quantity -= sold
        else:
            slot.current_quantity = 0
        slot.save()

        # 2. Математический расчет коэффициента заполненности (Ki)
        if slot.max_capacity > 0:
            ki = (slot.current_quantity / slot.max_capacity) * 100
            
            # Если остаток упал ниже 20%
            if ki < 20.0:
                # 3. Принцип идемпотентности (Проверяем, нет ли уже активной заявки на этот автомат)
                active_tasks = ServiceTask.objects.filter(
                    machine=slot.machine, 
                    status__in=['NEW', 'IN_PROGRESS']
                ).exists()
                
                # Если активных заявок нет - создаем новую!
                if not active_tasks:
                    desc = f"Прогноз: Критический остаток. Ячейка {slot.slot_number} ({slot.product.name} - осталось {slot.current_quantity} шт.)"
                    new_task = ServiceTask.objects.create(
                        machine=slot.machine,
                        description=desc
                    )
                    
                    print(f"Создана автоматическая заявка #{new_task.id} для автомата {slot.machine.id}")
                    
                    # 4. Рассылка Push-уведомлений
                    broadcast_telegram_message(new_task.id, slot.machine.id, desc)
                    broadcast_vk_message(new_task.id, slot.machine.id, desc)