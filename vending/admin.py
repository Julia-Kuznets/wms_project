from django.contrib import admin
from .models import Machine, Product, MachineSlot, ServiceTask

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('id', 'address', 'status')
    list_filter = ('status',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price')

@admin.register(MachineSlot)
class MachineSlotAdmin(admin.ModelAdmin):
    list_display = ('machine', 'slot_number', 'product', 'current_quantity', 'max_capacity')

@admin.register(ServiceTask)
class ServiceTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'machine', 'status', 'technician', 'created_at')
    list_filter = ('status',)

# Register your models here.
