from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _

from apps.modules.models import ContentType


class HomeworkInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if self.data.get("content_type") == ContentType.HOMEWORK.value:
            has_homework = False

            for form in self.forms:
                if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
                    has_homework = True
                    break

            if not has_homework:
                raise ValidationError(
                    _("{field} is required for {content_type}.").format(
                        field=_("homeworks"),
                        content_type=ContentType.HOMEWORK.label,
                    )
                )
