from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class QuizzesConfig(AppConfig):
    name = "apps.quizzes"
    verbose_name = _("Quizzes")
