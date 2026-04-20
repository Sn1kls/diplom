import json
import logging
import typing
import uuid

from django.apps import apps
from django.core.files.storage import default_storage
from django.http import JsonResponse
from ninja import File, Router, UploadedFile
from ninja_extra.status import HTTP_200_OK

from apps.admin_custom.permissions import StaffAuth

# from config.throttles import LoggingAuthRateThrottle as AuthRateThrottle

if typing.TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getLogger(__name__)


router = Router(auth=StaffAuth(), tags=["Admin"])


@router.post(
    "/save-order",
    response={200: dict},
    include_in_schema=False,
    # throttle=[AuthRateThrottle("30/m")],
)
def save_order(request: "HttpRequest"):
    try:
        data = json.loads(request.body)
        app_label, model_name, orders_list = data["app_label"], data["model_name"], data["orders"]

        if not (app_label and model_name and orders_list):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Missing app_label, model_name or orders parameters",
                },
                status=HTTP_200_OK,
            )  # Make status code as 200, because admin can find our API endpoint in console

        try:
            Model = apps.get_model(app_label, model_name)
        except LookupError as e:
            logger.error(f"{e.__class__.__name__}: model not found for {(app_label, model_name)}")
            return JsonResponse(
                {
                    "success": False,
                    "error": "Model not found",
                },
                status=HTTP_200_OK,
            )  # Make status code as 200, because admin can find our API endpoint in console

        objects_for_update = [
            Model(
                pk=obj["id"],
                order=obj["order"] + 1,
            )
            for obj in orders_list
        ]

        Model.objects.bulk_update(objects_for_update, ["order"])

        return JsonResponse(
            {
                "success": True,
            },
            status=HTTP_200_OK,
        )

    except json.JSONDecodeError as e:
        logger.error(f"{e.__class__.__name__}: {str(e)}")
        return JsonResponse(
            {
                "success": False,
                "error": "Error decoding JSON",
            },
            status=HTTP_200_OK,
        )  # Make status code as 200, because admin can find our API endpoint in console

    except Exception as e:
        logger.error(f"{e.__class__.__name__}: {str(e)}")
        return JsonResponse(
            {
                "success": False,
                "error": "Internal server error",
            },
            status=HTTP_200_OK,
        )  # Make status code as 200, because admin can find our API endpoint in console


@router.post(
    "/upload-files",
    response={200: dict},
    include_in_schema=False,
    # throttle=[AuthRateThrottle("30/m")],
)
def upload_files(request: "HttpRequest", file: UploadedFile = File()):
    file_ext = file.name.split(".")[-1]
    uuid_file_name = f"{uuid.uuid4()}.{file_ext}"
    path = default_storage.save(uuid_file_name, file)
    url = default_storage.url(path)
    return {"location": url}
