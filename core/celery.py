import os
from celery import Celery

# Устанавливаем настройки Django для Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Загружаем конфигурацию из настроек Django
# NAMESPACE='CELERY' означает, что все Celery-настройки
# должны быть с префиксом CELERY_ в settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически обнаруживаем задачи в файлах tasks.py
# в каждом приложении Django (например, vending/tasks.py)
app.autodiscover_tasks()

# Это просто для тестового вывода
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')