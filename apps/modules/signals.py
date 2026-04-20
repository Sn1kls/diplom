import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.modules.models import Lesson, Module, UserLessonProgress
from apps.users.services import UserProgressService

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver([post_save, post_delete], sender=UserLessonProgress)
def handle_user_score_update(sender, instance, **kwargs):
    try:
        if instance.user_fk:
            UserProgressService.recalculate_user_score(instance.user_fk)

    except Exception as e:
        logger.error(f"{e.__class__.__name__}: {e}")


@receiver(post_delete, sender=Module)
def reorder_modules_on_delete(sender, instance, **kwargs):
    with transaction.atomic():
        remaining_modules = Module.objects.select_for_update().order_by("order", "id")

        for index, module in enumerate(remaining_modules, start=1):
            if module.order != index:
                Module.objects.filter(pk=module.pk).update(order=index)


@receiver(post_delete, sender=Lesson)
def reorder_lessons_on_delete(sender, instance, **kwargs):
    with transaction.atomic():
        remaining_lessons = Lesson.objects.select_for_update().order_by("order", "id")

        for index, lesson in enumerate(remaining_lessons, start=1):
            if lesson.order != index:
                Lesson.objects.filter(pk=lesson.pk).update(order=index)


@receiver(post_save, sender=Lesson)
def handle_lesson_activation_change(sender, instance, created, update_fields=None, **kwargs):
    if created:
        return

    if update_fields and "is_active" not in update_fields:
        return

    user_ids = UserLessonProgress.objects.filter(
        lesson_fk=instance,
        is_completed=True,
    ).values_list("user_fk_id", flat=True)

    for user in User.objects.filter(id__in=user_ids).distinct():
        UserProgressService.recalculate_user_score(user)


@receiver(post_save, sender=Module)
def handle_module_activation_change(sender, instance, created, update_fields=None, **kwargs):
    if created:
        return

    if update_fields and "is_active" not in update_fields:
        return

    user_ids = UserLessonProgress.objects.filter(
        lesson_fk__module_fk=instance,
        is_completed=True,
    ).values_list("user_fk_id", flat=True)

    for user in User.objects.filter(id__in=user_ids).distinct():
        UserProgressService.recalculate_user_score(user)
