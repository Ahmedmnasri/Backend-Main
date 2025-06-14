from django.apps import AppConfig


class ChecklistsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'checklists'
    
    def ready(self):
        """Import signals when app is ready."""
        import checklists.signals  # noqa 