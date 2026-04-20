from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MentalHealthConfig(AppConfig):
    name = "apps.mental_health"
    verbose_name = _("Mental Health")

    def ready(self):
        import apps.mental_health.signals  # noqa
