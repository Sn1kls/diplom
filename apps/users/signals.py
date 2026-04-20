from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import GroupMembership, UserGroup

User = get_user_model()


@receiver(post_save, sender=User)
def assign_user_to_group(sender, instance, created, **kwargs):
    if created:
        active_group = (
            UserGroup.objects.filter(
                is_active=True,
            )
            .order_by("registration_started_at")
            .first()
        )

        if not active_group:
            return

        GroupMembership.objects.create(user=instance, group=active_group)
