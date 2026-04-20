from ninja import ModelSchema

from apps.homeworks.models import Homework, UserSubmission


class HomeworkSchema(ModelSchema):
    class Meta:
        model = Homework
        fields = [
            "id",
            "name",
            "description",
        ]


class UserSubmissionSchema(ModelSchema):
    class Meta:
        model = UserSubmission
        fields = [
            "id",
            "text_answer",
            "file_answer",
            "feedback",
            "is_approved",
            "created_at",
            "updated_at",
        ]
