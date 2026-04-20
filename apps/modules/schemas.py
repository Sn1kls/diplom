from ninja import Field, ModelSchema, Schema

from apps.homeworks.schemas import HomeworkSchema
from apps.modules.models import Lesson, Module, UserLessonProgress


class LessonSchemaExtendedBase(ModelSchema):
    quiz_id: int | None = Field(default=None, validation_alias="quiz_fk_id")
    homeworks: list[HomeworkSchema] | None

    class Meta:
        model = Lesson
        fields = [
            "id",
            "name",
            "content_type",
            "video_url",
            "audio_url",
            "description",
            "text_content",
            "order",
        ]


class LessonNavigationSchema(Schema):
    module_id: int
    lesson_id: int


class LessonSchemaExtended(LessonSchemaExtendedBase):
    previous_lesson: LessonNavigationSchema | None = None
    next_lesson: LessonNavigationSchema | None = None


class LessonSchema(ModelSchema):
    class Meta:
        model = Lesson
        fields = [
            "id",
            "name",
            "content_type",
            "order",
        ]


class UserLessonProgressSchema(ModelSchema):
    user_score: float

    class Meta:
        model = UserLessonProgress
        fields = ["id", "is_completed", "completed_at"]


class LessonCompletionRequest(Schema):
    module_id: int
    lesson_id: int


class ModuleSchema(ModelSchema):
    lessons: list[LessonSchema]

    class Meta:
        model = Module
        fields = [
            "id",
            "name",
            "description",
            "order",
        ]
