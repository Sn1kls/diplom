from django.utils.translation import gettext_lazy as _
from ninja_extra.status import HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT

from mixins.exceptions import AppException


class QuizAttemptNotCompletedError(AppException):
    message: str = _("Previous quiz attempt not completed.")
    status_code: int = HTTP_400_BAD_REQUEST


class AnswerAlreadyExistError(AppException):
    message: str = _("Answer for this question already exists.")
    status_code: int = HTTP_409_CONFLICT


class QuestionNotAnsweredError(AppException):
    message: str = _("Not all questions were answered.")
    status_code: int = HTTP_400_BAD_REQUEST
