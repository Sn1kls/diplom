from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline

from apps.homeworks.forms import HomeworkInlineFormSet
from apps.homeworks.models import Homework, UserSubmission


class HomeworkAdminInline(StackedInline):
    model = Homework
    formset = HomeworkInlineFormSet
    can_delete = True
    max_num = 1
    fk_name = "lesson_fk"
    exclude = ["is_auto_approved"]


@admin.register(UserSubmission)
class UserSubmissionAdmin(ModelAdmin):
    list_display = [
        "user_fk",
        "homework_fk",
        "feedback",
        "is_approved",
        "created_at",
        "date_review",
        "updated_at",
    ]
    readonly_fields = [
        "user_fk",
        "homework_fk",
        "text_answer",
        "file_answer",
        "created_at",
        "date_review",
        "updated_at",
    ]
    list_editable = ["feedback", "is_approved"]

    def has_add_permission(self, request, obj=None):
        return False
