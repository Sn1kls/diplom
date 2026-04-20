import typing
from datetime import datetime

from django.utils.translation import gettext_lazy as _
from ninja_extra.status import HTTP_403_FORBIDDEN

from mixins.exceptions import AppException


class EducationNotStartedError(AppException):
    message: str = _("You have not yet started the education and have not completed any lessons.")
    status_code: int = HTTP_403_FORBIDDEN


class PreviousLessonNotCompletedError(AppException):
    message: str = _("Previous lesson not completed.")
    status_code: int = HTTP_403_FORBIDDEN


class ModuleClosedError(AppException):
    message: str = _("The module is currently closed.")
    status_code: int = HTTP_403_FORBIDDEN

    def __init__(self, opening_date: typing.Optional[datetime]):
        self.opening_date = opening_date
        super().__init__(self.message, self.status_code)
