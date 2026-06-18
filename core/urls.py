
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from vending.views import MachineViewSet, AssignTaskView, ServiceTaskViewSet, CompleteTaskView 
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Настройка Swagger
schema_view = get_schema_view(
   openapi.Info(
      title="Vending API",
      default_version='v1',
      description="API для управления вендинговой сетью",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

router = DefaultRouter()
router.register(r'machines', MachineViewSet)
router.register(r'tasks', ServiceTaskViewSet) 

urlpatterns =[
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/v1/tasks/<int:task_id>/assign/', AssignTaskView.as_view()),
    path('api/v1/tasks/<int:task_id>/complete/', CompleteTaskView.as_view()),
    
    # Ссылки на Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]

