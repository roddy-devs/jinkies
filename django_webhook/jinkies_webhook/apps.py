"""
Django app configuration for Jinkies webhook.
"""
from django.apps import AppConfig


class JinkiesWebhookConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'jinkies_webhook'
    verbose_name = 'Jinkies Webhook Integration'
