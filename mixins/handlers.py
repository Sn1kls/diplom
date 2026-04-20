import logging

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import IntegrityError
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from ninja.responses import Response
from ninja_extra.status import (
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from apps.modules.exceptions import ModuleClosedError
from apps.users.exceptions import UserHasNotApprovedRequirementsError
from mixins.exceptions import AppException

logger = logging.getLogger(__name__)


def generic_exception_handler(_request: HttpRequest, exc: Exception) -> Response:
    logger.error(f"{exc.__class__.__name__}: {exc}")
    return Response(
        status=HTTP_500_INTERNAL_SERVER_ERROR,
        data={"detail": _("An internal error occurred.")},
    )


def app_exception_handler(_request: HttpRequest, exc: AppException) -> Response:
    logger.error(f"{exc.__class__.__name__}: {exc}")
    return Response(
        status=exc.status_code,
        data={"detail": exc.message},
    )


def integrity_exception_handler(_request: HttpRequest, exc: IntegrityError) -> Response:
    logger.error(f"{exc.__class__.__name__}: {exc}")
    return Response(
        status=HTTP_409_CONFLICT,
        data={"detail": _("Duplicate entry.")},
    )


def validation_exception_handler(_request: HttpRequest, exc: ValidationError) -> Response:
    logger.warning(f"{exc.__class__.__name__}: {exc}")
    return Response(
        status=HTTP_422_UNPROCESSABLE_ENTITY,
        data={"detail": str(exc)},
    )


def not_found_exception_handler(_request: HttpRequest, exc: ObjectDoesNotExist) -> Response:
    logger.warning(f"{exc.__class__.__name__}: {exc}")
    return Response(
        status=HTTP_404_NOT_FOUND,
        data={"detail": str(exc)},
    )


def permission_denied_exception_handler(_request: HttpRequest, exc: PermissionDenied) -> Response:
    logger.warning(f"{exc.__class__.__name__}: {exc}")
    return Response(
        status=HTTP_403_FORBIDDEN,
        data={"detail": str(exc)},
    )


def user_has_not_approved_requirements_exception_handler(
    _request: HttpRequest,
    exc: UserHasNotApprovedRequirementsError,
) -> Response:
    logger.warning(f"{exc.__class__.__name__}: {exc}")
    return Response(
        status=exc.status_code,
        data={"detail": exc.message},
    )


def module_closed_exception_handler(
    _request: HttpRequest,
    exc: ModuleClosedError,
):
    logger.warning(f"{exc.__class__.__name__}: {exc}")
    return Response(
        status=exc.status_code,
        data={
            "detail": exc.message,
            "opening_date": exc.opening_date,
        },
    )


exception_handlers = [
    (AppException, app_exception_handler),
    (IntegrityError, integrity_exception_handler),
    (ValidationError, validation_exception_handler),
    (ObjectDoesNotExist, not_found_exception_handler),
    (PermissionDenied, permission_denied_exception_handler),
    (UserHasNotApprovedRequirementsError, user_has_not_approved_requirements_exception_handler),
    (ModuleClosedError, module_closed_exception_handler),
    (Exception, generic_exception_handler),
]
