from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from tinymce.models import HTMLField

from apps.homeworks.utils import upload_homework_path

ALLOWED_DOC_EXTENSIONS = ["pdf", "docx", "txt"]


class Homework(models.Model):
    name = models.CharField(_("name"), max_length=100)
    description = HTMLField(_("description"), blank=True, null=True)
    lesson_fk = models.ForeignKey(
        "modules.Lesson",
        on_delete=models.CASCADE,
        related_name="homeworks",
        verbose_name=_("lesson"),
    )
    is_auto_approved = models.BooleanField(_("is auto-approved"), default=True)

    class Meta:
        verbose_name = _("Homework")
        verbose_name_plural = _("Homeworks")

    def __str__(self):
        return self.name


class UserSubmission(models.Model):
    user_fk = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="homeworks",
        verbose_name=_("user"),
    )
    homework_fk = models.ForeignKey(
        "homeworks.Homework",
        on_delete=models.CASCADE,
        related_name="homeworks",
        verbose_name=_("homework"),
    )
    text_answer = models.TextField(_("answer"), blank=True, null=True)
    file_answer = models.FileField(
        _("file answer"),
        upload_to=upload_homework_path,
        validators=[(FileExtensionValidator(allowed_extensions=ALLOWED_DOC_EXTENSIONS))],
        blank=True,
        null=True,
    )
    feedback = models.TextField(_("feedback"), blank=True, null=True)
    is_approved = models.BooleanField(_("is approved"), default=False)
    created_at = models.DateTimeField(_("date sent"), auto_now_add=True)
    date_review = models.DateTimeField(_("date reviewed"), blank=True, null=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("User Homework")
        verbose_name_plural = _("User Homeworks")
        constraints = [
            models.UniqueConstraint(
                fields=["user_fk", "homework_fk"],
                name="unique_user_homework",
            )
        ]

    def __str__(self):
        return f"{self.user_fk} - {self.homework_fk} - {self.created_at}"

    def save(
        self,
        *,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        if self.pk:
            old_instance = UserSubmission.objects.filter(pk=self.pk).only("feedback", "is_approved").first()

            if old_instance:
                feedback_changed = old_instance.feedback != self.feedback
                is_approved_changed = old_instance.is_approved != self.is_approved

                if feedback_changed or is_approved_changed:
                    self.date_review = timezone.now()

        if self.homework_fk.is_auto_approved:
            self.is_approved = True

        super(UserSubmission, self).save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def clean(self):
        super().clean()
        if not self.text_answer and not self.file_answer:
            raise ValidationError(_("Please provide either a text answer or a file answer for current homework."))
