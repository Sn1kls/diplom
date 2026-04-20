from django.db.models import Max, Sum

from apps.modules.models import ContentType, Lesson, UserLessonProgress
from apps.quizzes.models import Question, QuestionTypes, QuizAttempt


class UserProgressService:
    @staticmethod
    def get_total_possible_score() -> float:
        lessons_score = Lesson.active.aggregate(total=Sum("score"))["total"] or 0.0
        quiz_ids = Lesson.active.filter(content_type=ContentType.QUIZ).values_list("quiz_fk", flat=True)
        questions = Question.objects.filter(quiz_fk__in=quiz_ids)
        text_questions_count = questions.filter(question_type=QuestionTypes.TEXT).count()
        other_questions_count = questions.exclude(question_type=QuestionTypes.TEXT).count()
        quizzes_total = (text_questions_count * 2.0) + (other_questions_count * 1.0)
        return float(lessons_score) + quizzes_total

    @staticmethod
    def get_user_current_score(user) -> float:
        return float(user.score)

    @staticmethod
    def get_user_current_position(user) -> dict:
        completed_progress = UserLessonProgress.objects.filter(
            user_fk=user,
            is_completed=True,
        )

        completed_lesson_ids = set(completed_progress.values_list("lesson_fk_id", flat=True))

        next_lesson = (
            Lesson.active.select_related("module_fk")
            .exclude(id__in=completed_lesson_ids)
            .order_by("module_fk__order", "order", "id")
            .first()
        )

        if next_lesson is None:
            return {"current_module": None, "current_lesson": None}

        return {
            "current_module": {
                "id": next_lesson.module_fk.id,
                "name": next_lesson.module_fk.name,
                "order": next_lesson.module_fk.order,
            },
            "current_lesson": {
                "id": next_lesson.id,
                "name": next_lesson.name,
                "order": next_lesson.order,
            },
        }

    @staticmethod
    def recalculate_user_score(user) -> None:
        lesson_score = (
            UserLessonProgress.objects.filter(
                user_fk=user,
                is_completed=True,
                lesson_fk__module_fk__is_scored=True,
                lesson_fk__is_active=True,
                lesson_fk__module_fk__is_active=True,
            )
            .exclude(lesson_fk__content_type__in=[ContentType.QUIZ, ContentType.HOMEWORK])
            .aggregate(total_score=Sum("lesson_fk__score"))["total_score"]
            or 0.0
        )

        attempts = QuizAttempt.objects.filter(
            user_fk=user,
            is_completed=True,
            quiz_fk__lessons__is_active=True,
            quiz_fk__lessons__module_fk__is_active=True,
        ).distinct()
        quiz_score_sum = (
            attempts.values("quiz_fk").annotate(max_score=Max("score")).aggregate(total=Sum("max_score"))["total"]
            or 0.0
        )

        user.score = float(lesson_score) + float(quiz_score_sum)
        user.save(update_fields=["score"])
