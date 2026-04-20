from django.contrib import admin
from django.db import models
from tinymce.widgets import TinyMCE
from unfold.admin import ModelAdmin, TabularInline

from apps.quizzes.forms import AnswerInlineFormSet
from apps.quizzes.models import Answer, Question, QuestionResultMessageTemplate, Quiz, QuizAttempt, UserResponse


class AnswerInlineAdmin(TabularInline):
    model = Answer
    extra = 0
    tab = True
    fields = ["response", "is_correct", "order"]
    formset = AnswerInlineFormSet


@admin.register(QuestionResultMessageTemplate)
class QuestionResultMessageTemplateAdmin(admin.ModelAdmin):
    list_display = ["message", "is_correct"]
    search_fields = ["message"]


@admin.register(Quiz)
class QuizAdmin(ModelAdmin):
    list_display = ["name", "description"]
    search_fields = ["name"]
    formfield_overrides = {
        models.TextField: {
            "widget": TinyMCE(
                attrs={
                    "cols": 80,
                    "rows": 30,
                }
            )
        },
    }

    class Media:
        js = ("js/admin/text_editor.js",)


@admin.register(Question)
class QuestionAdmin(ModelAdmin):
    list_display = ["title", "question_type", "quiz_fk", "order"]
    list_editable = ["order", "quiz_fk"]
    list_filter = ["question_type", "quiz_fk"]
    exclude = ["order"]
    search_fields = ["title"]
    autocomplete_fields = ["correct_answer", "incorrect_answer"]
    inlines = [AnswerInlineAdmin]

    class Media:
        css = {
            "all": ("css/admin/drag-and-drop.css",),
        }
        js = (
            "js/admin/question_toggle.js",
            "js/admin/drag-and-drop.js",
        )


class UserResponseInlineAdmin(TabularInline):
    model = UserResponse
    extra = 0
    tab = True
    can_delete = False
    fields = [
        "question_fk",
        "is_correct",
        "points_awarded",
        "text_response",
        "selected_choice",
        "selected_choices",
    ]
    readonly_fields = ["question_fk", "text_response", "selected_choice", "selected_choices"]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(ModelAdmin):
    list_display = [
        "uid",
        "user_fk",
        "quiz_fk",
        "is_completed",
        "is_force_completed",
        "started_at",
        "finished_at",
        "score",
    ]
    list_filter = ["user_fk", "quiz_fk", "is_completed", "is_force_completed", "started_at", "finished_at"]
    search_fields = ["uid", "user_fk__email"]
    ordering = ["-started_at"]
    readonly_fields = ["score", "started_at"]
    inlines = [UserResponseInlineAdmin]
