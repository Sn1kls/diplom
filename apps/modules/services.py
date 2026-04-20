from typing import TYPE_CHECKING

from django.db.models import Q

from apps.modules.models import Lesson, UserLessonProgress

if TYPE_CHECKING:
    from apps.users.models import User


class LessonNavigationService:
    @staticmethod
    def build_navigation_item(lesson_row: dict | None) -> dict | None:
        if not lesson_row:
            return None

        return {"module_id": lesson_row["module_fk_id"], "lesson_id": lesson_row["id"]}

    @staticmethod
    def get_navigation_for_lesson(lesson: Lesson, user: "User") -> tuple[dict | None, dict | None]:
        navigation_queryset = Lesson.active.values("module_fk_id", "module_fk__order", "id", "order")

        module_order = lesson.module_fk.order
        lesson_order = lesson.order
        lesson_id = lesson.id

        previous_lesson = (
            navigation_queryset.filter(
                Q(module_fk__order__lt=module_order)
                | Q(module_fk__order=module_order, order__lt=lesson_order)
                | Q(module_fk__order=module_order, order=lesson_order, id__lt=lesson_id)
            )
            .order_by("-module_fk__order", "-order", "-id")
            .first()
        )

        next_lesson = (
            navigation_queryset.filter(
                Q(module_fk__order__gt=module_order)
                | Q(module_fk__order=module_order, order__gt=lesson_order)
                | Q(module_fk__order=module_order, order=lesson_order, id__gt=lesson_id)
            )
            .order_by("module_fk__order", "order", "id")
            .first()
        )

        completed_lesson_ids = UserLessonProgress.objects.filter(
            user_fk=user,
            is_completed=True,
        ).values_list("lesson_fk_id", flat=True)

        incomplete_previous_lesson = (
            navigation_queryset.filter(
                Q(module_fk__order__lt=module_order)
                | Q(module_fk__order=module_order, order__lt=lesson_order)
                | Q(module_fk__order=module_order, order=lesson_order, id__lt=lesson_id)
            )
            .exclude(id__in=completed_lesson_ids)
            .order_by("module_fk__order", "order", "id")
            .first()
        )

        if incomplete_previous_lesson:
            next_lesson = incomplete_previous_lesson

        return (
            LessonNavigationService.build_navigation_item(previous_lesson),
            LessonNavigationService.build_navigation_item(next_lesson),
        )
