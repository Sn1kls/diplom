import string
from typing import Optional

from django.db import transaction

from apps.quizzes.exceptions import AnswerAlreadyExistError
from apps.quizzes.models import Answer, Question, QuestionTypes, QuizAttempt, UserResponse


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text.strip().lower()


def calculate_score(
    question: Question,
    answer_ids: Optional[list[int]] = list[int] | None,
    default_correct_point: int = 1,
) -> tuple[bool, float]:
    is_correct = False
    points = 0.0
    correct_answers_qs = question.answers.filter(is_correct=True)

    if not answer_ids:
        return is_correct, points

    if question.question_type == QuestionTypes.SINGLE_CHOICE:
        if answer_ids and len(answer_ids) > 0 and correct_answers_qs.filter(id=answer_ids[0]).exists():
            is_correct = True
            points = float(default_correct_point)

    elif question.question_type == QuestionTypes.MULTIPLE_CHOICE:
        if answer_ids:
            user_set = set(answer_ids)
            correct_set = set(correct_answers_qs.values_list("id", flat=True))

            total_correct_options = len(correct_set)

            if total_correct_options > 0:
                user_correct_count = len(user_set.intersection(correct_set))
                user_wrong_count = len(user_set) - user_correct_count
                ratio = (user_correct_count - user_wrong_count) / total_correct_options
                final_ratio = max(0.0, ratio)
                points = final_ratio * default_correct_point
                is_correct = final_ratio == 1.0

    return is_correct, points


@transaction.atomic
def save_user_response(
    attempt: QuizAttempt,
    question: Question,
    text_response: Optional[str] = str | None,
    answer_ids: Optional[list[int]] = list[int] | None,
) -> UserResponse:
    if UserResponse.objects.filter(attempt_fk=attempt, question_fk=question).exists():
        raise AnswerAlreadyExistError()

    is_correct, points = calculate_score(question, answer_ids)
    user_response = UserResponse(
        attempt_fk=attempt,
        question_fk=question,
        is_correct=is_correct,
        points_awarded=points,
    )
    if question.question_type == QuestionTypes.TEXT:
        user_response.text_response = text_response
        user_response.points_awarded = 2
        user_response.is_correct = True

    elif question.question_type == QuestionTypes.SINGLE_CHOICE:
        if answer_ids:
            ans = Answer.objects.get(pk=answer_ids[0], question_fk=question)
            user_response.selected_choice = ans

    user_response.save()

    if question.question_type == QuestionTypes.MULTIPLE_CHOICE:
        if answer_ids:
            answers_qs = Answer.objects.filter(id__in=answer_ids, question_fk=question)
            user_response.selected_choices.set(answers_qs)

    return user_response
