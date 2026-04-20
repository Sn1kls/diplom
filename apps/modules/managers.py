from django.db import models


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class ActiveLessonManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True, module_fk__is_active=True)
