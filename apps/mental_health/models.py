from django.db import models
from django.db.models import Max
from django.utils.translation import gettext_lazy as _
from tinymce.models import HTMLField

from mixins.singleton import SingletonModel


class MentalHealth(SingletonModel):
    title = models.CharField(_("Title"), max_length=255)
    additional_content = HTMLField(_("Additional Content"))

    class Meta:
        verbose_name = _("Mental Health")
        verbose_name_plural = _("Mental Health")

    def __str__(self):
        return self.title


class MentalHealthQuestion(models.Model):
    question = models.TextField(_("question text"))
    min_score = models.PositiveIntegerField(_("minimum score"), default=0)
    max_score = models.PositiveIntegerField(_("maximum score"), default=5)
    order = models.PositiveIntegerField(_("order"), default=1)
    mental_health = models.ForeignKey(
        MentalHealth,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name=_("mental health"),
    )

    class Meta:
        verbose_name = _("mental health question")
        verbose_name_plural = _("mental health questions")
        ordering = ["order"]

    def __str__(self):
        return self.question

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.mental_health = MentalHealth.get_solo()
            max_order = MentalHealthQuestion.objects.aggregate(Max("order"))["order__max"]
            self.order = (max_order if max_order is not None else 0) + 1
        super().save(*args, **kwargs)


class MentalHealthAttemptNumber(models.IntegerChoices):
    BEFORE_START = 1, _("Before start education")
    AFTER_FINISH = 2, _("After finish education")


class MentalHealthAttempt(models.Model):
    number = models.IntegerField(_("number"), choices=MentalHealthAttemptNumber)
    score = models.PositiveIntegerField(_("score"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    user_fk = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="mental_health_attempts",
        verbose_name=_("mental health"),
    )
    mental_health = models.ForeignKey(
        MentalHealth,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name=_("mental health"),
    )

    class Meta:
        verbose_name = _("mental health attempt")
        verbose_name_plural = _("mental health attempts")
        constraints = [
            models.UniqueConstraint(
                fields=["user_fk", "number"],
                name="unique_user_number_mental_health",
            )
        ]

    def __str__(self):
        return f"{self.number} - {self.user_fk.email}"


class UserMentalHealthResponse(models.Model):
    attempt_fk = models.ForeignKey(
        MentalHealthAttempt,
        on_delete=models.CASCADE,
        related_name="user_mental_health_responses",
        verbose_name=_("mental health"),
    )
    question_fk = models.ForeignKey(
        MentalHealthQuestion,
        on_delete=models.CASCADE,
        related_name="user_mental_health_responses",
        verbose_name=_("mental health"),
    )
    response = models.PositiveIntegerField(_("response"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("mental health user mental health response")
        verbose_name_plural = _("mental health user mental health responses")

    def __str__(self):
        return f"{self.attempt_fk} - {self.question_fk} - {self.created_at}"
