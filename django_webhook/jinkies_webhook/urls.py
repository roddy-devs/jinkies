"""
URL configuration for Jinkies webhook app.
"""
from django.urls import path
from . import views

app_name = 'jinkies_webhook'

urlpatterns = [
    path('health/', views.health, name='health'),
    path('alert/', views.receive_alert, name='receive_alert'),
]
