from typing import Optional

from ninja import Field, ModelSchema, Schema

from apps.quizzes.models import Answer, Question, Quiz, QuizAttempt, UserResponse


class AnswerSchema(ModelSchema):
    class Meta:
        model = Answer
        fields = ["id", "response", "order"]


class QuestionSchema(ModelSchema):
    answers: list[AnswerSchema]

    class Meta:
        model = Question
        fields = ["id", "title", "question_type", "order"]


class QuizSchema(ModelSchema):
    questions: list[QuestionSchema]
    max_score: float

    @staticmethod
    def resolve_max_score(obj):
        return obj.max_score

    class Meta:
        model = Quiz
        fields = ["id", "name", "description"]


class QuizAttemptSchema(ModelSchema):
    class Meta:
        model = QuizAttempt
        fields = [
            "uid",
            "score",
            "is_completed",
            "is_force_completed",
            "started_at",
            "finished_at",
        ]


class QuizAttemptStartSchema(Schema):
    quiz_id: int = Field(...)
    lesson_id: int = Field(...)


class QuizAttemptBaseSchema(QuizAttemptStartSchema):
    attempt_uid: str = Field(...)
    is_force: bool = Field(False)


class QuizAttemptFinishedSchema(ModelSchema):
    max_score: float

    @staticmethod
    def resolve_max_score(obj):
        return obj.quiz_fk.max_score

    class Meta:
        model = QuizAttempt
        fields = ["uid", "score", "is_completed", "is_force_completed", "started_at", "finished_at"]


class UserQuizResponseSchema(QuizAttemptBaseSchema):
    question_id: int = Field(...)
    text_response: Optional[str] = Field(None)
    answer_ids: Optional[list[int]] = Field(default_factory=list)


class UserResponseSchema(ModelSchema):
    class Meta:
        model = UserResponse
        fields = ["id", "is_correct", "points_awarded"]


class AnswerResponseSchema(ModelSchema):
    class Meta:
        model = Answer
        fields = ["id", "response", "is_correct", "order"]


class UserResponseWithCorrectnessSchema(UserResponseSchema):
    correct_answers: list[AnswerResponseSchema] = []
    correct_answer_message: Optional[str] = None
    incorrect_answer_message: Optional[str] = None

    @staticmethod
    def resolve_correct_answer_message(obj):
        if obj.question_fk and obj.question_fk.correct_answer:
            return obj.question_fk.correct_answer.message
        return None

    @staticmethod
    def resolve_incorrect_answer_message(obj):
        if obj.question_fk and obj.question_fk.incorrect_answer:
            return obj.question_fk.incorrect_answer.message
        return None
