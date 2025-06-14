from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        """
        Called when Django starts up.
        Signals are disabled - all user management handled in admin.py
        """
        pass  # No signals to import

