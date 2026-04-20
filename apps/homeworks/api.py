import logging
from typing import TYPE_CHECKING, Optional

from django.utils.translation import gettext_lazy as _
from ninja import File, Form, Router, UploadedFile
from ninja.responses import Response
from ninja_extra.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_422_UNPROCESSABLE_ENTITY
from ninja_jwt.authentication import JWTAuth

from apps.homeworks.exceptions import UserSubmissionAlreadyExistException
from apps.homeworks.models import Homework, UserSubmission
from apps.homeworks.schemas import HomeworkSchema, UserSubmissionSchema
from apps.users.utils import __check_has_user_approved_requirements, __check_module_access

# from config.throttles import LoggingAuthRateThrottle as AuthRateThrottle

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getLogger(__name__)
router = Router(tags=["Homeworks"])


@router.get(
    "/submission/{homework_id}",
    response={
        HTTP_200_OK: UserSubmissionSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_result_submission_by_homework_id(request: "HttpRequest", homework_id: int):
    user = request.user
    homework = Homework.objects.get(id=homework_id)
    module_id = homework.lesson_fk.module_fk.id

    __check_has_user_approved_requirements(user)
    __check_module_access(user, module_id)

    user_submission = UserSubmission.objects.get(
        user_fk=user,
        homework_fk_id=homework_id,
    )
    return Response(
        status=HTTP_200_OK,
        data=UserSubmissionSchema.from_orm(user_submission).dict(),
    )


@router.post(
    "/submission",
    response={
        HTTP_201_CREATED: UserSubmissionSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("10/m")],
)
def send_homework(
    request: "HttpRequest",
    homework_id: int = Form(...),
    text_answer: Optional[str] = Form(None),
    file_answer: Optional[UploadedFile] = File(None),
):
    try:
        if not text_answer and not file_answer:
            return Response(
                status=HTTP_422_UNPROCESSABLE_ENTITY,
                data={"detail": _("Please provide either a text answer or a file answer for current homework.")},
            )

        user = request.user
        homework = Homework.objects.get(id=homework_id)
        module_id = homework.lesson_fk.module_fk.id

        __check_has_user_approved_requirements(user)
        __check_module_access(user, module_id)

        user_submission, created = UserSubmission.objects.get_or_create(
            user_fk=user,
            homework_fk=homework,
            defaults={
                "text_answer": text_answer,
                "file_answer": file_answer,
            },
        )
        if not created:
            raise UserSubmissionAlreadyExistException()

        return Response(
            status=HTTP_201_CREATED,
            data=UserSubmissionSchema.from_orm(user_submission).dict(),
        )

    except UserSubmissionAlreadyExistException as e:
        return Response(
            status=e.status_code,
            data={"detail": str(e)},
        )


@router.put(
    "/submission/{homework_id}",
    response={
        HTTP_200_OK: UserSubmissionSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("10/m")],
)
def edit_homework_submission(
    request: "HttpRequest",
    homework_id: int,
    text_answer: Optional[str] = Form(None),
    file_answer: Optional[UploadedFile] = File(None),
):
    if not text_answer and not file_answer:
        return Response(
            status=HTTP_422_UNPROCESSABLE_ENTITY,
            data={"detail": _("Please provide either a text answer or a file answer for current homework.")},
        )

    user = request.user
    homework = Homework.objects.get(id=homework_id)
    module_id = homework.lesson_fk.module_fk.id

    __check_has_user_approved_requirements(user)
    __check_module_access(user, module_id)

    submission = UserSubmission.objects.get(user_fk=user, homework_fk=homework)
    submission.text_answer = text_answer
    submission.file_answer = file_answer
    submission.save(update_fields=["text_answer", "file_answer"])

    return Response(
        status=HTTP_200_OK,
        data=UserSubmissionSchema.from_orm(submission).dict(),
    )


@router.get(
    "/{homework_id}",
    response={
        HTTP_200_OK: HomeworkSchema,
    },
    auth=JWTAuth(),
    # throttle=[AuthRateThrottle("50/m")],
)
def get_homework_by_id(request: "HttpRequest", homework_id: int):
    homework = Homework.objects.get(pk=homework_id)
    module_id = homework.lesson_fk.module_fk.id

    __check_has_user_approved_requirements(request.user)
    __check_module_access(request.user, module_id)

    return Response(
        status=HTTP_200_OK,
        data=HomeworkSchema.from_orm(homework).dict(),
    )
