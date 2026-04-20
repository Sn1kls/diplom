import logging
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Prefetch
from ninja import Router
from ninja.responses import Response
from ninja_extra.status import HTTP_200_OK
from ninja_jwt.authentication import JWTAuth

from apps.modules.exceptions import EducationNotStartedError, PreviousLessonNotCompletedError
from apps.modules.models import Lesson, Module, UserLessonProgress
from apps.modules.schemas import (
    LessonCompletionRequest,
    LessonSchemaExtended,
    LessonSchemaExtendedBase,
    ModuleSchema,
    UserLessonProgressSchema,
)
from apps.modules.services import LessonNavigationService
from apps.users.utils import __check_has_user_approved_requirements, __check_lesson_access, __check_module_access

# from config.throttles import LoggingAuthRateThrottle as AuthRateThrottle

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getLogger(__name__)
router = Router(tags=["Modules"])


@router.get(
    "/",
    response={
        HTTP_200_OK: list[ModuleSchema],
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_modules(request: "HttpRequest"):
    __check_has_user_approved_requirements(request.user)
    modules = Module.active.prefetch_related(
        Prefetch(
            "lessons",
            queryset=Lesson.active.all(),
        )
    ).all()
    modules_list = [ModuleSchema.from_orm(module).dict() for module in modules]
    return Response(
        status=HTTP_200_OK,
        data=modules_list,
    )


@router.get(
    "/{module_id}",
    response={
        HTTP_200_OK: ModuleSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_module_by_id(request: "HttpRequest", module_id: int):
    __check_has_user_approved_requirements(request.user)
    __check_module_access(request.user, module_id)

    module = Module.active.prefetch_related(
        Prefetch(
            "lessons",
            queryset=Lesson.active.all(),
        )
    ).get(pk=module_id)

    return Response(
        status=HTTP_200_OK,
        data=ModuleSchema.from_orm(module).dict(),
    )


@router.get(
    "/{module_id}/lessons",
    response={
        HTTP_200_OK: list[LessonSchemaExtendedBase],
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_lessons_for_module_by_module_id(request: "HttpRequest", module_id: int):
    __check_has_user_approved_requirements(request.user)
    __check_module_access(request.user, module_id)

    lessons = Lesson.active.filter(module_fk_id=module_id)
    lessons_list = [LessonSchemaExtendedBase.from_orm(lesson) for lesson in lessons]
    return Response(
        status=HTTP_200_OK,
        data=lessons_list,
    )


@router.get(
    "/{module_id}/lessons/{lesson_id}",
    response={
        HTTP_200_OK: LessonSchemaExtended,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_lesson_for_module_by_lesson_id(request: "HttpRequest", module_id: int, lesson_id: int):
    try:
        user = request.user
        __check_has_user_approved_requirements(request.user)
        __check_lesson_access(user, module_id, lesson_id)

        lesson = Lesson.active.get(
            pk=lesson_id,
            module_fk_id=module_id,
        )

        previous_lesson, next_lesson = LessonNavigationService.get_navigation_for_lesson(lesson, user)
        lesson.previous_lesson = previous_lesson
        lesson.next_lesson = next_lesson

        return Response(
            status=HTTP_200_OK,
            data=LessonSchemaExtended.from_orm(lesson).dict(),
        )

    except (EducationNotStartedError, PreviousLessonNotCompletedError) as e:
        return Response(
            status=e.status_code,
            data={"detail": e.message},
        )


@router.post(
    "/lessons/complete",
    response={
        HTTP_200_OK: UserLessonProgressSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("30/m")],
)
def complete_lesson(request: "HttpRequest", payload: LessonCompletionRequest):
    try:
        user = request.user
        __check_has_user_approved_requirements(request.user)
        __check_lesson_access(user, payload.module_id, payload.lesson_id)

        lesson = Lesson.active.get(
            pk=payload.lesson_id,
            module_fk_id=payload.module_id,
        )

        with transaction.atomic():
            progress, created = UserLessonProgress.objects.get_or_create(
                user_fk=user,
                lesson_fk=lesson,
                defaults={"is_completed": True},
            )

            if created or not progress.is_completed:
                if not created:
                    progress.is_completed = True
                    progress.save()

        return Response(
            status=HTTP_200_OK,
            data=UserLessonProgressSchema.from_orm(progress).dict(),
        )

    except (EducationNotStartedError, PreviousLessonNotCompletedError) as e:
        return Response(
            status=e.status_code,
            data={"detail": e.message},
        )
