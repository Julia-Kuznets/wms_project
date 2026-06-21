import os
import random
import requests
from celery import shared_task
from django.contrib.auth import get_user_model
from .models import MachineSlot, ServiceTask

User = get_user_model()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
VK_TOKEN = os.environ.get("VK_TOKEN") # <-- Добавили токен ВК

def broadcast_message_to_all(task_id, machine_id, description):
    """Широковещательная рассылка в Telegram и ВКонтакте"""
    
    # === 1. РАССЫЛКА В TELEGRAM ===
    if BOT_TOKEN:
        tg_users = User.objects.filter(username__iregex=r'^\d+$')
        tg_text = (
            f"🚨 <b>АВТОМАТИЧЕСКАЯ ЗАЯВКА #{task_id}</b>\n\n"
            f"<b>Автомат:</b> ID {machine_id}\n"
            f"<b>Проблема:</b> {description}\n\n"
            f"<i>Зайди в меню /tasks, чтобы взять в работу!</i>"
        )
        for tech in tg_users:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {"chat_id": tech.username, "text": tg_text, "parse_mode": "HTML"}
            try:
                requests.post(url, json=payload, timeout=5)
            except Exception as e:
                print(f"Ошибка отправки в TG: {e}")

    # === 2. РАССЫЛКА В ВКОНТАКТЕ ===
    if VK_TOKEN:
        # Ищем техников ВК (их имена в БД начинаются с vk_)
        vk_users = User.objects.filter(username__startswith='vk_')
        vk_text = (
            f"🚨 АВТОМАТИЧЕСКАЯ ЗАЯВКА #{task_id}\n\n"
            f"Автомат: ID {machine_id}\n"
            f"Проблема: {description}\n\n"
            f"Напиши команду /tasks, чтобы принять её в работу!"
        )
        for tech in vk_users:
            # Вытаскиваем чистый числовой ID из "vk_123456"
            vk_id = tech.username.replace('vk_', '')
            url = "https://api.vk.com/method/messages.send"
            payload = {
                "user_id": vk_id,
                "message": vk_text,
                "random_id": random.randint(1, 1000000),
                "access_token": VK_TOKEN,
                "v": "5.131"
            }
            try:
                requests.post(url, data=payload, timeout=5)
            except Exception as e:
                print(f"Ошибка отправки в ВК: {e}")



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
                    broadcast_message_to_all(new_task.id, slot.machine.id, desc)