from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator



User = get_user_model()

class Machine(models.Model):
    STATUS_CHOICES =[
        ('ACTIVE', 'В работе'),
        ('BROKEN', 'Сломан'),
        ('MAINTENANCE', 'На обслуживании'),
    ]
    address = models.CharField(max_length=255, verbose_name="Адрес установки")

    latitude = models.FloatField(
        null=True, blank=True, verbose_name="Широта",
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)]
    )
    longitude = models.FloatField(
        null=True, blank=True, verbose_name="Долгота",
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)]
    )
 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name="Статус")

    def __str__(self):
        return f"Автомат #{self.id} ({self.address})"

class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name="Наименование")
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Цена")

    def __str__(self):
        return self.name

class MachineSlot(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='slots')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    
    # Регулярное выражение: Заглавная латинская буква, затем от 1 до 2 цифр (A1, B12)
    slot_number = models.CharField(
        max_length=10, 
        verbose_name="Номер ячейки (A1, B2)",
        validators=[RegexValidator(
            regex=r'^[A-Z]\d{1,2}$',
            message="Формат ячейки должен быть Буква+Цифра (например: A1, B12)"
        )]
    )
    current_quantity = models.PositiveIntegerField(default=0, verbose_name="Текущий остаток")
    max_capacity = models.PositiveIntegerField(verbose_name="Вместимость")


    def __str__(self):
        return f"{self.machine} - {self.slot_number} ({self.product.name})"

class ServiceTask(models.Model):
    STATUS_CHOICES =[
        ('NEW', 'Новая'),
        ('IN_PROGRESS', 'В работе'),
        ('DONE', 'Выполнена'),
    ]
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    technician = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Техник")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW', verbose_name="Статус")
    description = models.TextField(verbose_name="Описание проблемы/Код ошибки", default="Неизвестная ошибка")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")

    def __str__(self):
        return f"Заявка #{self.id} - Автомат {self.machine.id}"
   
