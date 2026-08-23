from django.apps import AppConfig


class MarketplaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "marketplace"

    def ready(self):
        # Import signal handlers only after Django has loaded every model.
        from . import signals  # noqa: F401
