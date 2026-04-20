from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HomeworksConfig(AppConfig):
    name = "apps.homeworks"
    verbose_name = _("Homeworks")
