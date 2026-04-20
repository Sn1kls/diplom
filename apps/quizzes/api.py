import logging
from typing import TYPE_CHECKING

from django.db import transaction
from ninja import Router
from ninja.responses import Response
from ninja_extra.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND
from ninja_jwt.authentication import JWTAuth

from apps.modules.models import Lesson
from apps.quizzes.exceptions import AnswerAlreadyExistError, QuizAttemptNotCompletedError
from apps.quizzes.models import Answer, Question, Quiz, QuizAttempt
from apps.quizzes.schemas import (
    QuizAttemptBaseSchema,
    QuizAttemptFinishedSchema,
    QuizAttemptSchema,
    QuizAttemptStartSchema,
    QuizSchema,
    UserQuizResponseSchema,
    UserResponseWithCorrectnessSchema,
)
from apps.quizzes.services import save_user_response
from apps.users.services import UserProgressService
from apps.users.utils import __check_has_user_approved_requirements, __check_module_access

# from config.throttles import LoggingAuthRateThrottle as AuthRateThrottle

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getLogger(__name__)
router = Router(tags=["Quizzes"])


@router.post(
    "/attempts",
    response={
        HTTP_201_CREATED: QuizAttemptSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("10/m")],
)
def start_quiz(request: "HttpRequest", payload: QuizAttemptStartSchema):
    try:
        user = request.user
        __check_has_user_approved_requirements(user)

        lesson = (
            Lesson.objects.filter(
                pk=payload.lesson_id,
                quiz_fk_id=payload.quiz_id,
            )
            .select_related("module_fk")
            .first()
        )

        __check_module_access(user, lesson.module_fk.id)

        quiz_attempt, created = QuizAttempt.objects.get_or_create(
            user_fk=user,
            quiz_fk_id=payload.quiz_id,
            is_completed=False,
            lesson_context=lesson,
        )
        if not created:
            raise QuizAttemptNotCompletedError()

        return Response(
            status=HTTP_201_CREATED,
            data=QuizAttemptSchema.from_orm(quiz_attempt).dict(),
        )

    except QuizAttemptNotCompletedError as e:
        return Response(
            status=e.status_code,
            data={
                "detail": str(e),
                "uid": quiz_attempt.uid,
            },
        )


@router.post(
    "/attempts/answers",
    response={
        HTTP_201_CREATED: UserResponseWithCorrectnessSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("30/m")],
)
def add_answer(request: "HttpRequest", payload: UserQuizResponseSchema):
    try:
        user = request.user
        __check_has_user_approved_requirements(user)

        attempt = QuizAttempt.objects.select_related("lesson_context__module_fk").get(
            uid=payload.attempt_uid,
            user_fk=user,
            is_completed=False,
        )
        if attempt.lesson_context:
            __check_module_access(user, attempt.lesson_context.module_fk.id)

        question = Question.objects.get(
            pk=payload.question_id,
            quiz_fk_id=payload.quiz_id,
        )

        with transaction.atomic():
            user_response = save_user_response(
                attempt=attempt,
                question=question,
                text_response=payload.text_response,
                answer_ids=payload.answer_ids,
            )

        response_data = UserResponseWithCorrectnessSchema.from_orm(user_response)
        correct_answers = Answer.objects.filter(is_correct=True, question_fk=question)
        response_data.correct_answers = list(correct_answers)

        return Response(
            status=HTTP_201_CREATED,
            data=response_data.dict(),
        )

    except AnswerAlreadyExistError as e:
        return Response(
            status=e.status_code,
            data={"detail": str(e)},
        )


@router.post(
    "/attempts/results",
    response={
        HTTP_200_OK: QuizAttemptFinishedSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("10/m")],
)
def finish_quiz(request: "HttpRequest", payload: QuizAttemptBaseSchema):
    try:
        user = request.user
        __check_has_user_approved_requirements(user)

        quiz_attempt = QuizAttempt.objects.get(
            uid=payload.attempt_uid,
            user_fk_id=user.id,
            quiz_fk_id=payload.quiz_id,
            is_completed=False,
        )

        if quiz_attempt.lesson_context:
            __check_module_access(user, quiz_attempt.lesson_context.module_fk.id)

        if not payload.is_force and not quiz_attempt.can_be_finished:
            raise QuizAttemptNotCompletedError()

        quiz_attempt.finish()
        UserProgressService.recalculate_user_score(user)
        return Response(
            status=HTTP_200_OK,
            data=QuizAttemptFinishedSchema.from_orm(quiz_attempt).dict(),
        )

    except QuizAttemptNotCompletedError as e:
        return Response(
            status=e.status_code,
            data={"detail": str(e)},
        )


@router.get(
    "/{module_id}",
    response={
        HTTP_200_OK: list[QuizSchema],
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_quizzes(request: "HttpRequest", module_id: int):
    __check_has_user_approved_requirements(request.user)
    __check_module_access(request.user, module_id)

    quizzes = (
        Quiz.objects.filter(
            lessons__module_fk_id=module_id,
        )
        .distinct()
        .prefetch_related("questions__answers")
    )
    quizzes_list = [QuizSchema.from_orm(quiz).dict() for quiz in quizzes]
    if not quizzes_list:
        return Response(
            status=HTTP_404_NOT_FOUND,
            data={"detail": "No quizzes found."},
        )

    return Response(
        status=HTTP_200_OK,
        data=quizzes_list,
    )


@router.get(
    "/{module_id}/{quiz_id}",
    response={
        HTTP_200_OK: QuizSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_quiz_by_id(request: "HttpRequest", module_id: int, quiz_id: int):
    __check_has_user_approved_requirements(request.user)
    __check_module_access(request.user, module_id)

    quiz = Quiz.objects.get(
        pk=quiz_id,
        lessons__module_fk_id=module_id,
    )
    return Response(
        status=HTTP_200_OK,
        data=QuizSchema.from_orm(quiz).dict(),
    )


@router.get(
    "/{module_id}/{quiz_id}/attempts",
    response={
        HTTP_200_OK: list[QuizAttemptSchema],
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_quiz_attempts(request: "HttpRequest", module_id: int, quiz_id: int):
    __check_has_user_approved_requirements(request.user)
    __check_module_access(request.user, module_id)

    users_attempts = QuizAttempt.objects.filter(
        user_fk=request.user,
        quiz_fk_id=quiz_id,
        lesson_context__module_fk_id=module_id,
    )

    attempts_list = [QuizAttemptSchema.from_orm(attempt).dict() for attempt in users_attempts]
    if not attempts_list:
        return Response(
            status=HTTP_404_NOT_FOUND,
            data={"detail": "No quiz attempts found."},
        )

    return Response(
        status=HTTP_200_OK,
        data=attempts_list,
    )
