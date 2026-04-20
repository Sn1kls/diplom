from django.utils.translation import gettext_lazy as _
from ninja_extra.status import HTTP_500_INTERNAL_SERVER_ERROR


class AppException(Exception):
    message: str = _("An internal error occurred.")
    status_code: int = HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str = None, status_code: int = None):
        self.message = message or self.message
        self.status_code = status_code or self.status_code
        super().__init__(self.message)
