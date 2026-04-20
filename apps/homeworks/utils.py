import typing
import uuid

if typing.TYPE_CHECKING:
    from apps.homeworks.models import UserSubmission


def upload_homework_path(instance: "UserSubmission", filename: str) -> str:
    file_ext = filename.split(".")[-1]
    uuid_file_name = f"{uuid.uuid4()}.{file_ext}"
    return f"homeworks/hw_{instance.homework_fk.id}/user_{instance.user_fk.id}/{uuid_file_name}"
