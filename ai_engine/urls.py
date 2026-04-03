from django.urls import path
from .views import trigger_generation, check_status

urlpatterns = [
    path('generate/', trigger_generation),
    path('status/<str:task_id>/', check_status),
]