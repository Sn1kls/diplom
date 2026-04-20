from django.utils.translation import gettext_lazy as _
from ninja_extra.status import HTTP_409_CONFLICT

from mixins.exceptions import AppException


class UserSubmissionAlreadyExistException(AppException):
    message: str = _("User submission already exists.")
    status_code: int = HTTP_409_CONFLICT
