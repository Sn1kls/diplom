from django.utils.translation import gettext_lazy as _
from ninja_extra.status import HTTP_403_FORBIDDEN

from mixins.exceptions import AppException


class NoPreviousAnswerException(AppException):
    message: str = _("No response was provided in the first iteration.")
    status_code: int = HTTP_403_FORBIDDEN


class NotCompletedEducationException(AppException):
    message: str = _("For the second iteration of the test, education must be completed.")
    status_code: int = HTTP_403_FORBIDDEN
