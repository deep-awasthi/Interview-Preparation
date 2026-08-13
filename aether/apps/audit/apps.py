from django.apps import AppConfig

class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aether.apps.audit"
    label = "aether_audit"
