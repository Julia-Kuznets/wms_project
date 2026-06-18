from rest_framework import serializers
from .models import Machine, ServiceTask

class MachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Machine
        fields = '__all__'

class ServiceTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceTask
        fields = '__all__' #плохая практика
        