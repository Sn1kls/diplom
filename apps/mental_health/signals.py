from django.db.models import Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.mental_health.models import UserMentalHealthResponse


@receiver([post_save, post_delete], sender=UserMentalHealthResponse)
def update_attempt_score(sender, instance, **kwargs):
    attempt = instance.attempt_fk
    total_score = attempt.user_mental_health_responses.aggregate(total=Sum("response"))["total"] or 0
    attempt.__class__.objects.filter(pk=attempt.pk).update(score=total_score)
