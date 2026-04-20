from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Max
from django.utils.translation import gettext_lazy as _
from tinymce.models import HTMLField

from apps.modules.managers import ActiveLessonManager, ActiveManager

ALLOWED_VIDEO_EXTENSIONS = ["mp4", "webm", "mov"]
ALLOWED_AUDIO_EXTENSIONS = ["mp3", "m4a", "wav", "ogg"]


class ContentType(models.TextChoices):
    TEXT = "text", _("Text")
    VIDEO = "video", _("Video")
    AUDIO = "audio", _("Audio")
    QUIZ = "quiz", _("Quiz")
    HOMEWORK = "homework", _("Homework")


class Module(models.Model):
    name = models.CharField(_("name"), max_length=120)
    description = HTMLField(_("description"), blank=True, null=True)
    order = models.PositiveIntegerField(_("order"), default=1)
    is_scored = models.BooleanField(_("is scored"), default=True)
    is_active = models.BooleanField(_("is active"), default=True)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        verbose_name = _("Module")
        verbose_name_plural = _("Modules")
        ordering = ["order"]

    def __str__(self):
        return f"{self.order}:{self.name or self.id}"

    def save(
        self,
        *,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        if self._state.adding:
            max_order = Module.objects.aggregate(Max("order"))["order__max"]
            self.order = (max_order if max_order is not None else 0) + 1
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class Lesson(models.Model):
    name = models.CharField(_("name"), max_length=120)
    module_fk = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name=_("Module"),
    )
    content_type = models.CharField(_("content type"), max_length=120, choices=ContentType.choices)
    quiz_fk = models.ForeignKey(
        "quizzes.Quiz",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name=_("Quiz"),
        limit_choices_to={"lessons__isnull": True},
    )
    video_url = models.FileField(
        _("video url"),
        upload_to="videos",
        validators=[(FileExtensionValidator(allowed_extensions=ALLOWED_VIDEO_EXTENSIONS))],
        blank=True,
        null=True,
        help_text=_("Allowed formats"),
    )
    audio_url = models.FileField(
        _("audio url"),
        upload_to="audio",
        validators=[(FileExtensionValidator(allowed_extensions=ALLOWED_AUDIO_EXTENSIONS))],
        blank=True,
        null=True,
        help_text=_("Allowed formats"),
    )
    description = HTMLField(_("description"), blank=True, null=True)
    text_content = HTMLField(_("text content"), blank=True, null=True)
    score = models.FloatField(_("score"), default=0.0)
    order = models.PositiveIntegerField(_("order"), default=1)
    is_active = models.BooleanField(_("is active"), default=True)

    objects = models.Manager()
    active = ActiveLessonManager()

    class Meta:
        verbose_name = _("Lesson")
        verbose_name_plural = _("Lessons")
        ordering = ["order"]

    def __str__(self):
        return self.name or self.id

    def save(
        self,
        *,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        if self._state.adding:
            max_order = Lesson.objects.aggregate(Max("order"))["order__max"]
            self.order = (max_order if max_order is not None else 0) + 1

        if self.content_type not in [ContentType.AUDIO, ContentType.VIDEO]:
            self.description = None

        match self.content_type:
            case ContentType.TEXT:
                self.score = 2
            case ContentType.AUDIO:
                self.score = 2
            case ContentType.VIDEO:
                self.score = 3
            case _:
                self.score = 0  # Set the score as zero because other content type have their own scoring algorithms
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class UserLessonProgress(models.Model):
    user_fk = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="lesson_progress",
        verbose_name=_("User"),
    )
    lesson_fk = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progress",
        verbose_name=_("Lesson"),
    )
    is_completed = models.BooleanField(_("is completed"), default=False)
    completed_at = models.DateTimeField(_("completed at"), auto_now_add=True)

    class Meta:
        verbose_name = _("User Lesson Progress")
        verbose_name_plural = _("User Lesson Progresses")
        constraints = [
            models.UniqueConstraint(
                fields=["user_fk", "lesson_fk"],
                name="unique_user_lesson_progress",
            )
        ]

    def __str__(self):
        return f"{self.user_fk} - {self.lesson_fk} - {self.is_completed}"

    @property
    def user_score(self) -> float:
        return self.user_fk.score
