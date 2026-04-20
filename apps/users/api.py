import logging
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from ninja import Router
from ninja.responses import Response
from ninja.throttling import AnonRateThrottle
from ninja_extra.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.exceptions import TokenError
from ninja_jwt.schema import TokenRefreshInputSchema, TokenRefreshOutputSchema
from ninja_jwt.tokens import RefreshToken

from apps.modules.models import UserLessonProgress
from apps.users.exceptions import (
    EmailAlreadyExistsError,
    InvalidActivationTokenError,
    InvalidOldPasswordError,
    InvalidPasswordResetTokenError,
    PhoneAlreadyExistsError,
    UserAlreadyActiveError,
    UserInvalidCredentialError,
    UserNotActiveError,
)
from apps.users.schemas import (
    ActivateUserSchema,
    ChatInvitationSchema,
    ForgotPasswordSchema,
    ResetPasswordSchema,
    UserChatsSchema,
    UserLessonProgressResponseSchema,
    UserLoginSchema,
    UserProgressSchema,
    UserRegisterSchema,
    UserResponseSchema,
    UserUpdateSchema,
)
from apps.users.services import UserProgressService
from apps.users.utils import (
    __check_has_user_approved_requirements,
    get_general_chat_invitation,
    get_user_chat_invitation,
    send_activation_email,
    send_chat_invitation_email,
    send_reset_password_email,
    verify_user_token,
)

# from config.throttles import LoggingAuthRateThrottle as AuthRateThrottle
from mixins.schemas import ErrorSchema, MessageSchema

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getLogger(__name__)
User = get_user_model()
router = Router(tags=["Users"])


@router.post(
    "/register",
    response={
        HTTP_201_CREATED: UserResponseSchema,
        HTTP_409_CONFLICT: ErrorSchema,
        HTTP_500_INTERNAL_SERVER_ERROR: ErrorSchema,
    },
    auth=None,
    throttle=[AnonRateThrottle("5/m")],
)
def register_user(request: "HttpRequest", payload: UserRegisterSchema):
    try:
        if payload.email and User.objects.filter(email=payload.email).exists():
            raise EmailAlreadyExistsError()

        if User.objects.filter(phone=payload.phone).exists():
            raise PhoneAlreadyExistsError()

        user_data = payload.model_dump(exclude_none=True)
        user_data["is_active"] = False

        user = User.objects.create_user(**user_data)

        frontend_url = request.build_absolute_uri("/")
        send_activation_email(user, frontend_url)

        return Response(
            status=HTTP_201_CREATED,
            data=UserResponseSchema.from_orm(user).dict(),
        )

    except EmailAlreadyExistsError as e:
        logger.error(f"{e.__class__.__name__}: {e}")
        return Response(
            status=e.status_code,
            data={"error": str(e)},
        )

    except PhoneAlreadyExistsError as e:
        logger.error(f"{e.__class__.__name__}: {e}")
        return Response(
            status=e.status_code,
            data={"error": str(e)},
        )


@router.post(
    "/activate",
    response={HTTP_200_OK: MessageSchema, HTTP_400_BAD_REQUEST: ErrorSchema},
    auth=None,
    throttle=[AnonRateThrottle("5/m")],
)
def activate_user(request: "HttpRequest", payload: ActivateUserSchema):
    try:
        if not payload.uid or not payload.token:
            raise InvalidActivationTokenError()

        user = verify_user_token(payload.uid, payload.token)
        if user is None:
            raise InvalidActivationTokenError()

        if user.is_active:
            raise UserAlreadyActiveError()

        user.is_active = True
        user.save(update_fields=["is_active"])
        send_chat_invitation_email(user)

        return Response(
            status=HTTP_200_OK,
            data={"detail": _("Your account has been successfully activated.")},
        )

    except (InvalidActivationTokenError, UserAlreadyActiveError) as e:
        logger.error(f"{e.__class__.__name__}: {e}")
        return Response(
            status=e.status_code,
            data={"error": str(e)},
        )


@router.post(
    "/login",
    response={
        HTTP_200_OK: TokenRefreshOutputSchema,
        HTTP_400_BAD_REQUEST: ErrorSchema,
        HTTP_404_NOT_FOUND: ErrorSchema,
    },
    auth=None,
    throttle=[AnonRateThrottle("10/m")],
)
def login_user(request: "HttpRequest", payload: UserLoginSchema):
    try:
        user = User.objects.get(email=payload.email)

        if not user.is_active:
            raise UserNotActiveError()

        if not user.check_password(payload.password):
            raise UserInvalidCredentialError()

        refresh = RefreshToken.for_user(user)
        return Response(
            status=HTTP_200_OK,
            data=TokenRefreshOutputSchema(
                access=str(refresh.access_token),
                refresh=str(refresh),
            ),
        )

    except (UserInvalidCredentialError, UserNotActiveError) as e:
        logger.error(f"{e.__class__.__name__}: {e}")
        return Response(
            status=e.status_code,
            data={"error": str(e)},
        )


@router.post(
    "/refresh",
    response={
        HTTP_200_OK: TokenRefreshOutputSchema,
        HTTP_422_UNPROCESSABLE_ENTITY: ErrorSchema,
    },
    auth=None,
    throttle=[AnonRateThrottle("10/m")],
)
def refresh_token(request: "HttpRequest", payload: TokenRefreshInputSchema):
    try:
        refresh = RefreshToken(payload.refresh)
        return Response(
            status=HTTP_200_OK,
            data=TokenRefreshOutputSchema(
                access=str(refresh.access_token),
                refresh=str(refresh),
            ),
        )
    except TokenError as e:
        logger.error(f"{e.__class__.__name__}: {e}")
        return Response(
            status=HTTP_400_BAD_REQUEST,
            data={"error": str(e)},
        )


@router.get(
    "/me/progress",
    response={
        HTTP_200_OK: UserProgressSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_my_progress(request: "HttpRequest"):
    user = request.user

    current_score = UserProgressService.get_user_current_score(user)
    total_score = UserProgressService.get_total_possible_score()
    position = UserProgressService.get_user_current_position(user)

    return Response(
        status=HTTP_200_OK,
        data=UserProgressSchema(
            current_score=current_score,
            total_score=total_score,
            **position,
        ).dict(),
    )


@router.get(
    "/me/lessons/progress",
    response={
        HTTP_200_OK: list[UserLessonProgressResponseSchema],
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_lessons_progress(request: "HttpRequest"):
    user = request.user
    __check_has_user_approved_requirements(user)
    progress = UserLessonProgress.objects.filter(user_fk=user)
    return Response(
        status=HTTP_200_OK,
        data=[UserLessonProgressResponseSchema.from_orm(progress_item).dict() for progress_item in progress],
    )


@router.get(
    "/me",
    response={
        HTTP_200_OK: UserResponseSchema,
        HTTP_404_NOT_FOUND: ErrorSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_me(request: "HttpRequest"):
    user = request.user
    return Response(
        status=HTTP_200_OK,
        data=UserResponseSchema.from_orm(user).dict(),
    )


@router.get(
    "/me/chats",
    response={HTTP_200_OK: UserChatsSchema},
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_my_chats(request: "HttpRequest"):
    user = request.user

    personal_invitation = get_user_chat_invitation(user)
    general_invitation = get_general_chat_invitation(user)

    return Response(
        status=HTTP_200_OK,
        data=UserChatsSchema(
            personal_chat=ChatInvitationSchema.from_orm(personal_invitation) if personal_invitation else None,
            general_chat=ChatInvitationSchema.from_orm(general_invitation) if general_invitation else None,
        ).dict(),
    )


@router.post(
    "/forgot-password",
    response={HTTP_200_OK: MessageSchema},
    auth=None,
    throttle=[AnonRateThrottle("3/m")],
)
def forgot_password(request: "HttpRequest", payload: ForgotPasswordSchema):
    user = User.objects.get(email=payload.email, is_active=True)
    frontend_url = request.build_absolute_uri("/")
    send_reset_password_email(user, frontend_url)

    return Response(
        status=HTTP_200_OK,
        data={"detail": _("If an account exists for this email, a password reset link has been sent.")},
    )


@router.post(
    "/reset-password",
    response={HTTP_200_OK: MessageSchema, HTTP_400_BAD_REQUEST: ErrorSchema},
    auth=None,
    throttle=[AnonRateThrottle("5/m")],
)
def reset_password(request: "HttpRequest", payload: ResetPasswordSchema):
    try:
        user = verify_user_token(payload.uid, payload.token)
        if not user:
            raise InvalidPasswordResetTokenError()
        user.set_password(payload.new_password)
        user.save()

        return Response(
            status=HTTP_200_OK,
            data={"detail": _("Your password has been successfully reset.")},
        )
    except InvalidPasswordResetTokenError as e:
        logger.error(f"{e.__class__.__name__}: {e}")
        return Response(
            status=e.status_code,
            data={"error": str(e)},
        )


@router.patch(
    "/me",
    response={
        HTTP_200_OK: UserResponseSchema,
        HTTP_409_CONFLICT: ErrorSchema,
        HTTP_500_INTERNAL_SERVER_ERROR: ErrorSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def edit_me(request: "HttpRequest", payload: UserUpdateSchema):
    user = request.user
    try:
        data = payload.model_dump(exclude_none=True)

        old_password = data.pop("old_password", None)
        new_password = data.pop("new_password", None)
        new_password_confirm = data.pop("new_password_confirm", None)

        if all([old_password, new_password, new_password_confirm]):
            if not user.check_password(old_password):
                raise InvalidOldPasswordError()

            user.set_password(new_password)

        if (phone := data.get("phone", None)) and User.objects.filter(phone=phone).exclude(pk=user.pk).exists():
            raise PhoneAlreadyExistsError()

        if data.pop("has_approved_requirements", False):
            user.has_approved_requirements = True

        for key, value in data.items():
            setattr(user, key, value)

        user.save()

        return Response(
            status=HTTP_200_OK,
            data=UserResponseSchema.from_orm(user).dict(),
        )

    except (PhoneAlreadyExistsError, InvalidOldPasswordError) as e:
        logger.error(f"{e.__class__.__name__}: {e}")
        return Response(status=e.status_code, data={"error": str(e)})


@router.delete(
    "/me",
    response={
        HTTP_200_OK: MessageSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def delete_me(request: "HttpRequest"):
    user = request.user
    user.is_active = False
    user.save(update_fields=["is_active"])

    return Response(
        status=HTTP_200_OK,
        data={"detail": _("Account deleted successfully.")},
    )
