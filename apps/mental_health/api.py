import logging
from typing import TYPE_CHECKING

from django.db.models import Max
from ninja import Router
from ninja.responses import Response
from ninja_extra.status import HTTP_200_OK, HTTP_201_CREATED
from ninja_jwt.authentication import JWTAuth

from apps.mental_health.exceptions import NoPreviousAnswerException, NotCompletedEducationException
from apps.mental_health.models import (
    MentalHealth,
    MentalHealthAttempt,
    MentalHealthAttemptNumber,
    UserMentalHealthResponse,
)
from apps.mental_health.schemas import MentalHealthAttemptSchema, MentalHealthResponseSchema, MentalHealthSchema
from apps.modules.models import Lesson, UserLessonProgress
from apps.users.utils import __check_has_user_approved_requirements

# from config.throttles import LoggingAuthRateThrottle as AuthRateThrottle

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getLogger(__name__)
router = Router(tags=["Mental Health"])


@router.get(
    "/",
    response={
        HTTP_200_OK: MentalHealthSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_mental_health(request: "HttpRequest"):
    __check_has_user_approved_requirements(request.user)
    mental_health = MentalHealth.get_solo()
    return Response(data=MentalHealthSchema.from_orm(mental_health).dict(), status=HTTP_200_OK)


@router.post(
    "/answers",
    response={
        HTTP_201_CREATED: MentalHealthAttemptSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("10/m")],
)
def add_answers_for_mental_health_test(request: "HttpRequest", payload: MentalHealthResponseSchema):
    try:
        __check_has_user_approved_requirements(request.user)

        mental_health_test = MentalHealth.get_solo()
        if payload.number != MentalHealthAttemptNumber.BEFORE_START.value:
            if not MentalHealthAttempt.objects.filter(
                user_fk=request.user,
                mental_health=mental_health_test,
            ).exists():
                raise NoPreviousAnswerException()

            max_order = Lesson.objects.aggregate(Max("order"))["order__max"]
            if not UserLessonProgress.objects.filter(
                user_fk=request.user,
                lesson_fk__order=max_order,
                is_completed=True,
            ).exists():
                raise NotCompletedEducationException()

        mental_health_attempt = MentalHealthAttempt.objects.create(
            number=payload.number,
            user_fk=request.user,
            mental_health=mental_health_test,
        )

        responses = [
            UserMentalHealthResponse(
                attempt_fk=mental_health_attempt,
                question_fk_id=answer.question_id,
                response=answer.response,
            )
            for answer in payload.answers
        ]
        UserMentalHealthResponse.objects.bulk_create(responses)

        mental_health_attempt.score = sum(answer.response for answer in payload.answers)
        mental_health_attempt.save()

        return Response(
            data=MentalHealthAttemptSchema.from_orm(mental_health_attempt).dict(),
            status=HTTP_201_CREATED,
        )

    except (NoPreviousAnswerException, NotCompletedEducationException) as e:
        return Response(
            data={"detail": e.message},
            status=e.status_code,
        )


@router.get(
    "/answers",
    response={
        HTTP_200_OK: list[MentalHealthAttemptSchema],
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_answers_for_mental_health_test(request: "HttpRequest"):
    __check_has_user_approved_requirements(request.user)
    mental_health_attempts = MentalHealthAttempt.objects.filter(user_fk=request.user)
    mental_health_attempts_list = [
        MentalHealthAttemptSchema.from_orm(mental_health_attempt).dict()
        for mental_health_attempt in mental_health_attempts
    ]
    return Response(
        data=mental_health_attempts_list,
        status=HTTP_200_OK,
    )
