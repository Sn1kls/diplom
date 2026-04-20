from django.contrib import admin
from django.db import models
from django.db.models import OuterRef, Subquery
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from tinymce.widgets import TinyMCE
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import AutocompleteSelectFilter

from apps.homeworks.admin import HomeworkAdminInline
from apps.modules.forms import LessonAdminForm
from apps.modules.models import Lesson, Module, UserLessonProgress


@admin.register(Module)
class ModuleAdmin(ModelAdmin):
    list_display = ["name", "description", "is_active", "order"]
    list_editable = ["is_active", "order"]
    exclude = ["order"]
    search_fields = ["name"]
    formfield_overrides = {
        models.TextField: {
            "widget": TinyMCE(
                attrs={
                    "cols": 80,
                    "rows": 30,
                },
            )
        },
    }

    class Media:
        css = {
            "all": ("css/admin/drag-and-drop.css",),
        }
        js = (
            "js/admin/text_editor.js",
            "js/admin/drag-and-drop.js",
        )


@admin.register(Lesson)
class LessonAdmin(ModelAdmin):
    list_display = ["name", "content_type", "module_fk", "is_active", "order"]
    list_editable = ["content_type", "module_fk", "is_active", "order"]
    list_filter = ["module_fk", "content_type"]
    exclude = ["order", "score"]
    search_fields = ["name", "content_type"]
    inlines = [HomeworkAdminInline]
    form = LessonAdminForm
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
        css = {
            "all": ("css/admin/drag-and-drop.css",),
        }
        js = (
            "js/admin/lesson_toggle.js",
            "js/admin/text_editor.js",
            "js/admin/drag-and-drop.js",
        )


@admin.register(UserLessonProgress)
class UserLessonProgressAdmin(ModelAdmin):
    list_display = ["user_history_link", "lesson_fk", "completed_at"]
    list_display_links = ["lesson_fk"]
    list_filter = ["completed_at", ("user_fk", AutocompleteSelectFilter)]
    search_fields = ["user_fk__email", "lesson_fk__name"]
    list_filter_submit = True

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related("user_fk", "lesson_fk")

        filtered_user = request.GET.get("user_fk__id__exact")
        if filtered_user:
            return queryset.filter(user_fk_id=filtered_user).order_by("-completed_at", "-id")

        latest_completed_progress_id = (
            UserLessonProgress.objects.filter(
                user_fk=OuterRef("user_fk"),
                is_completed=True,
            )
            .order_by("-completed_at", "-id")
            .values("id")[:1]
        )

        return queryset.filter(id=Subquery(latest_completed_progress_id)).order_by("user_fk__email")

    @admin.display(description=_("User"), ordering="user_fk__email")
    def user_history_link(self, obj):
        history_url = (
            f"{reverse('admin:modules_userlessonprogress_changelist')}?"
            f"{urlencode({'user_fk__id__exact': obj.user_fk_id})}"
        )
        return format_html('<a href="{}">{}</a>', history_url, obj.user_fk.email)
