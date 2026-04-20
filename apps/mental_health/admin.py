from django.contrib import admin
from django.db import models
from tinymce.widgets import TinyMCE
from unfold.admin import ModelAdmin, TabularInline

from apps.mental_health.models import MentalHealth, MentalHealthAttempt, MentalHealthQuestion, UserMentalHealthResponse


class UserMentalHealthResponseTabularAdmin(TabularInline):
    model = UserMentalHealthResponse
    extra = 0
    tab = True
    can_delete = False


@admin.register(MentalHealth)
class MentalHealthAdmin(ModelAdmin):
    list_display = ["title", "additional_content"]
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

    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return True


@admin.register(MentalHealthQuestion)
class MentalHealthQuestionAdmin(ModelAdmin):
    list_display = ["question", "min_score", "max_score", "order"]
    list_editable = ["order"]
    readonly_fields = ["min_score", "max_score", "mental_health"]
    exclude = ["order"]

    class Media:
        css = {
            "all": ("css/admin/drag-and-drop.css",),
        }
        js = (
            "js/admin/text_editor.js",
            "js/admin/drag-and-drop.js",
        )


@admin.register(MentalHealthAttempt)
class MentalHealthAttemptAdmin(ModelAdmin):
    list_display = ["number", "score", "user_fk", "mental_health"]
    readonly_fields = ["score"]
    inlines = [UserMentalHealthResponseTabularAdmin]
