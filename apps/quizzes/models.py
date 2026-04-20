import uuid

from django.db import models
from django.db.models import Case, FloatField, Max, Sum, Value, When
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from tinymce.models import HTMLField


class Quiz(models.Model):
    name = models.CharField(_("name"), max_length=100)
    description = HTMLField(_("description"), blank=True, null=True)

    class Meta:
        verbose_name = _("Quiz")
        verbose_name_plural = _("Quizzes")

    def __str__(self):
        return self.name

    @property
    def max_score(self) -> float:
        aggregation = self.questions.aggregate(
            total=Sum(
                Case(
                    When(question_type=QuestionTypes.TEXT, then=Value(2.0)),
                    default=Value(1.0),
                    output_field=FloatField(),
                )
            )
        )
        return aggregation["total"] or 0.0


class QuestionResultMessageTemplate(models.Model):
    message = models.TextField(_("message"))
    is_correct = models.BooleanField(_("is correct?"), default=False)

    class Meta:
        verbose_name = _("Question result message")
        verbose_name_plural = _("Question result messages")

    def __str__(self):
        return self.message


class QuestionTypes(models.TextChoices):
    TEXT = "text", _("Text")
    MULTIPLE_CHOICE = "multiple", _("Multiple Choice")
    SINGLE_CHOICE = "single", _("Single Choice")


class Question(models.Model):
    title = models.TextField(_("title"), max_length=200)
    question_type = models.CharField(_("question type"), max_length=8, choices=QuestionTypes.choices)
    order = models.PositiveIntegerField(_("order"), default=1)
    quiz_fk = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name=_("quiz"),
    )
    correct_answer = models.ForeignKey(
        QuestionResultMessageTemplate,
        on_delete=models.CASCADE,
        related_name="correct_for_questions",
        verbose_name=_("correct answer"),
        limit_choices_to={"is_correct": True},
        blank=True,
        null=True,
    )
    incorrect_answer = models.ForeignKey(
        QuestionResultMessageTemplate,
        on_delete=models.CASCADE,
        related_name="incorrect_for_questions",
        verbose_name=_("incorrect answer"),
        limit_choices_to={"is_correct": False},
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")
        ordering = ["order"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self._state.adding:
            max_order = Question.objects.aggregate(Max("order"))["order__max"]
            self.order = (max_order if max_order is not None else 0) + 1
        super().save(*args, **kwargs)


class Answer(models.Model):
    response = models.CharField(_("response"), max_length=120)
    is_correct = models.BooleanField(_("is correct"), default=False)
    order = models.PositiveIntegerField(_("order"), default=1)
    question_fk = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name=_("question"),
    )

    class Meta:
        verbose_name = _("Answer")
        verbose_name_plural = _("Answers")
        ordering = ["order"]

    def __str__(self):
        return self.response

    def save(self, *args, **kwargs):
        if self._state.adding:
            max_order = Answer.objects.aggregate(Max("order"))["order__max"]
            self.order = (max_order if max_order is not None else 0) + 1
        super().save(*args, **kwargs)


class QuizAttempt(models.Model):
    uid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_("UID"),
    )
    user_fk = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
        verbose_name=_("user"),
    )
    quiz_fk = models.ForeignKey(
        "quizzes.Quiz",
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
        verbose_name=_("quiz"),
    )
    lesson_context = models.ForeignKey(
        "modules.Lesson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Context Lesson"),
    )
    score = models.FloatField(_("score"), default=0.0)
    started_at = models.DateTimeField(_("created at"), auto_now_add=True)
    finished_at = models.DateTimeField(_("finished at"), null=True, blank=True)
    is_completed = models.BooleanField(_("is completed"), default=False)
    is_force_completed = models.BooleanField(_("is completed force"), default=False)

    _EXPECTED_MISSING_QUESTIONS_COUNT_TO_FINISH = 0

    class Meta:
        verbose_name = _("Quiz Attempt")
        verbose_name_plural = _("Quiz Attempts")
        ordering = ["-started_at"]

    def __str__(self):
        return str(self.uid)

    def force_finish(self) -> None:
        self._complete_quiz()
        self.is_force_completed = True
        self.save()

    def finish(self) -> None:
        self._complete_quiz()
        aggregation = self.user_responses.aggregate(total_points=Sum("points_awarded"))
        total_score = aggregation["total_points"] or 0.0
        self.score = total_score
        self.save()

    def _complete_quiz(self) -> None:
        self.is_completed = True
        self.finished_at = timezone.now()

    @property
    def missing_questions(self) -> set[int]:
        all_questions_ids = set(self.quiz_fk.questions.values_list("id", flat=True))
        answered_questions_ids = set(self.user_responses.values_list("question_fk_id", flat=True))
        return all_questions_ids - answered_questions_ids

    @property
    def can_be_finished(self) -> bool:
        return len(self.missing_questions) == self._EXPECTED_MISSING_QUESTIONS_COUNT_TO_FINISH


class UserResponse(models.Model):
    attempt_fk = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="user_responses",
        verbose_name=_("user response"),
    )
    question_fk = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
        verbose_name=_("question"),
    )
    text_response = models.TextField(_("response text"), blank=True, null=True)
    selected_choice = models.ForeignKey(
        Answer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="selected_in_responses",
        verbose_name=_("selected choices"),
    )
    selected_choices = models.ManyToManyField(
        Answer,
        blank=True,
        related_name="selected_in_multiple_responses",
    )
    is_correct = models.BooleanField(_("is correct"), default=False)
    points_awarded = models.FloatField(_("points awarded"), default=0.0)

    class Meta:
        verbose_name = _("User Response")
        verbose_name_plural = _("User Responses")
        constraints = [
            models.UniqueConstraint(fields=["attempt_fk", "question_fk"], name="unique_attempt_question_response")
        ]

    def __str__(self):
        return f"{self.attempt_fk} - {self.question_fk} ({self.selected_choice})"
