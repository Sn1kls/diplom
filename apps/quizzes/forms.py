from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.quizzes.models import QuestionTypes


class AnswerInlineFormSet(forms.BaseInlineFormSet):
    MIN_CORRECT_ANSWERS = 1

    def __count_correct_answers(self) -> int | None:
        correct_answers = 0
        for form in self.forms:
            if not form.is_valid():
                return None

            if form.cleaned_data and not form.cleaned_data.get("DELETE"):
                if form.cleaned_data.get("is_correct"):
                    correct_answers += 1
        return correct_answers

    def clean(self):
        super().clean()

        if any(self.errors) or not (question := self.instance):
            return

        correct_answers = self.__count_correct_answers()

        if correct_answers > self.MIN_CORRECT_ANSWERS and question.question_type == QuestionTypes.SINGLE_CHOICE:
            raise ValidationError(_("Questions of type SINGLE_CHOICE can have only one correct answer."))

        if correct_answers < self.MIN_CORRECT_ANSWERS and question.question_type != QuestionTypes.TEXT:
            raise ValidationError(_("Please select at least one correct answer (depending on the type of question)."))
