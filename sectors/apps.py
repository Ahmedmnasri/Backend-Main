from django.apps import AppConfig


class SectorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sectors'
    
    def ready(self):
        """Import signal handlers"""
        pass  # Supabase sync removed