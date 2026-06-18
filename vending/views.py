from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from .models import Machine, ServiceTask
from .serializers import MachineSerializer, ServiceTaskSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class MachineViewSet(viewsets.ReadOnlyModelViewSet):
    """API для получения списка автоматов"""
    queryset = Machine.objects.all()
    serializer_class = MachineSerializer


class ServiceTaskViewSet(viewsets.ModelViewSet):
    """API для управления заявками (Создание, чтение, удаление)"""
    queryset = ServiceTask.objects.all()
    serializer_class = ServiceTaskSerializer


class AssignTaskView(APIView):
    """API для принятия заявки техником из Telegram"""
    
    @transaction.atomic
    def post(self, request, task_id):
        task = ServiceTask.objects.select_for_update().filter(id=task_id).first()
        
        if not task:
            return Response({"error": "Заявка не найдена"}, status=404)
            
        if task.status != 'NEW':
            return Response({"error": "Заявка уже распределена"}, status=400)
            
        # Получаем Telegram ID от бота
        telegram_id = request.data.get('user_id') 
        
        # МАГИЯ ЗДЕСЬ: Ищем юзера с таким именем, а если его нет — создаем!
        tech_user, created = User.objects.get_or_create(username=str(telegram_id))
        
        task.status = 'IN_PROGRESS'
        task.technician = tech_user  # Присваиваем реального пользователя БД
        task.save()
        
        return Response({"message": "Заявка успешно принята в работу"}, status=200)

class CompleteTaskView(APIView):
    """API для завершения заявки техником"""
    
    @transaction.atomic
    def post(self, request, task_id):
        task = ServiceTask.objects.select_for_update().filter(id=task_id).first()
        
        if not task:
            return Response({"error": "Заявка не найдена"}, status=404)
            
        if task.status != 'IN_PROGRESS':
            return Response({"error": "Заявку нельзя завершить (она не в работе)"}, status=400)
            
        # Меняем статус на ВЫПОЛНЕНА
        task.status = 'DONE'
        task.save()
        
        # ЭМУЛЯЦИЯ РАБОТЫ ТЕХНИКА:
        # Раз он приехал, значит он заполнил автомат. Восполняем остатки до максимума!
        slots = task.machine.slots.all()
        for slot in slots:
            slot.current_quantity = slot.max_capacity
            slot.save()
            
        return Response({"message": "Работа завершена, остатки восполнены"}, status=200)



