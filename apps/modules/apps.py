from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ModulesConfig(AppConfig):
    name = "apps.modules"
    verbose_name = _("Modules")

    def ready(self):
        import apps.modules.signals  # noqa
