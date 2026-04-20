from django import forms
from django.utils.translation import gettext_lazy as _

from apps.modules.models import ALLOWED_AUDIO_EXTENSIONS, ALLOWED_VIDEO_EXTENSIONS, ContentType, Lesson


class LessonAdminForm(forms.ModelForm):
    REQUIRED_FIELDS_MAP = {
        ContentType.TEXT.value: ["text_content"],
        ContentType.VIDEO.value: ["video_url"],
        ContentType.AUDIO.value: ["audio_url"],
        ContentType.QUIZ.value: ["quiz_fk"],
        ContentType.HOMEWORK.value: [],
    }

    OPTIONAL_FIELDS_MAP = {
        ContentType.VIDEO.value: ["description"],
        ContentType.AUDIO.value: ["description"],
    }

    class Meta:
        model = Lesson
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            "audio_url"
        ].help_text = f"{self.fields['audio_url'].help_text}: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}"
        self.fields[
            "video_url"
        ].help_text = f"{self.fields['video_url'].help_text}: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        self.fields["audio_url"].widget.attrs["accept"] = ",".join(
            f".{extension}" for extension in ALLOWED_AUDIO_EXTENSIONS
        )
        self.fields["video_url"].widget.attrs["accept"] = ",".join(
            f".{extension}" for extension in ALLOWED_VIDEO_EXTENSIONS
        )

    def _clean_errors(self, content_type: str, cleaned_data: dict):
        all_content_fields = ["text_content", "video_url", "audio_url", "description", "quiz_fk"]
        required_fields = self.REQUIRED_FIELDS_MAP.get(content_type, [])
        optional_fields = self.OPTIONAL_FIELDS_MAP.get(content_type, [])
        active_fields = required_fields + optional_fields

        for field in all_content_fields:
            if field not in active_fields:
                if field in self.errors:
                    del self.errors[field]
                cleaned_data[field] = None

    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get("content_type")
        self._clean_errors(content_type, cleaned_data)

        text_content = cleaned_data.get("text_content")
        video_url = cleaned_data.get("video_url")
        audio_url = cleaned_data.get("audio_url")
        quiz_fk = cleaned_data.get("quiz_fk")

        errors_message = _("{field} is required for {content_type}.")

        match content_type:
            case ContentType.TEXT:
                if not text_content:
                    self.add_error(
                        "text_content",
                        errors_message.format(
                            field=_("text_content"),
                            content_type=ContentType.TEXT.label,
                        ),
                    )

            case ContentType.VIDEO:
                if not video_url:
                    self.add_error(
                        "video_url",
                        errors_message.format(
                            field=_("video_url"),
                            content_type=ContentType.VIDEO.label,
                        ),
                    )

            case ContentType.AUDIO:
                if not audio_url:
                    self.add_error(
                        "audio_url",
                        errors_message.format(
                            field=_("audio_url"),
                            content_type=ContentType.AUDIO.label,
                        ),
                    )

            case ContentType.QUIZ:
                if not quiz_fk:
                    self.add_error(
                        "quiz_fk",
                        errors_message.format(
                            field=_("quiz_fk"),
                            content_type=ContentType.QUIZ.label,
                        ),
                    )

        return cleaned_data
