from django.utils.translation import gettext_lazy as _
from ninja_extra.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_409_CONFLICT,
)

from mixins.exceptions import AppException


class UserAlreadyExistsError(AppException):
    message: str = _("A user with the provided data already exists.")
    status_code: int = HTTP_409_CONFLICT


class EmailAlreadyExistsError(UserAlreadyExistsError):
    message: str = _("A user with this email address already exists.")


class PhoneAlreadyExistsError(UserAlreadyExistsError):
    message: str = _("A user with this phone number already exists.")


class UserInvalidCredentialError(AppException):
    message: str = _("Invalid credentials.")
    status_code: int = HTTP_400_BAD_REQUEST


class UserNotActiveError(AppException):
    message: str = _("User is not active.")
    status_code: int = HTTP_403_FORBIDDEN


class InvalidActivationTokenError(AppException):
    message: str = _("Invalid or expired activation link.")
    status_code: int = HTTP_400_BAD_REQUEST


class InvalidPasswordResetTokenError(AppException):
    message: str = _("This password reset link has expired. Please request a new one.")
    status_code: int = HTTP_400_BAD_REQUEST


class UserAlreadyActiveError(AppException):
    message: str = _("User is already active.")
    status_code: int = HTTP_400_BAD_REQUEST


class InvalidOldPasswordError(AppException):
    message: str = _("The old password is incorrect.")
    status_code: int = HTTP_400_BAD_REQUEST


class UserHasNotApprovedRequirementsError(AppException):
    message: str = _("User has not approved the requirements.")
    status_code: int = HTTP_403_FORBIDDEN
