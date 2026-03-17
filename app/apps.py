from django.apps import AppConfig
from django.apps import AppConfig

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app' # ou 'website', use o nome da sua pasta

    def ready(self):
        import app.signals # <--- Adicione essa linha


class AppConfig(AppConfig):
    name = 'app'
