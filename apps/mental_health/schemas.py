from ninja import Field, ModelSchema, Schema

from apps.mental_health.models import (
    MentalHealth,
    MentalHealthAttempt,
    MentalHealthAttemptNumber,
    MentalHealthQuestion,
    UserMentalHealthResponse,
)


class MentalHealthQuestionSchema(ModelSchema):
    class Meta:
        model = MentalHealthQuestion
        fields = [
            "id",
            "question",
            "min_score",
            "max_score",
            "order",
        ]


class MentalHealthSchema(ModelSchema):
    questions: list[MentalHealthQuestionSchema]

    class Meta:
        model = MentalHealth
        fields = [
            "id",
            "title",
            "additional_content",
        ]


class MentalHealthAnswerSchema(Schema):
    question_id: int = Field(...)
    response: int = Field(...)


class MentalHealthResponseSchema(Schema):
    number: MentalHealthAttemptNumber = Field(...)
    answers: list[MentalHealthAnswerSchema] = Field(...)


class UserMentalHealthResponseSchema(ModelSchema):
    question_id: int = Field(validation_alias="question_fk_id")

    class Meta:
        model = UserMentalHealthResponse
        fields = [
            "id",
            "response",
            "created_at",
        ]


class MentalHealthAttemptSchema(ModelSchema):
    responses: list[UserMentalHealthResponseSchema] = Field(validation_alias="user_mental_health_responses")

    class Meta:
        model = MentalHealthAttempt
        fields = [
            "id",
            "number",
            "score",
            "created_at",
        ]
