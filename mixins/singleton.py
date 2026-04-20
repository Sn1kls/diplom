from django.core.cache import cache
from django.db import models


class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.__flush_cache()
        self.__class__.objects.exclude(id=self.id).delete()
        super(SingletonModel, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.__flush_cache()
        super(SingletonModel, self).delete(*args, **kwargs)

    @classmethod
    def load(cls):
        try:
            return cls.objects.get()
        except cls.DoesNotExist:
            return cls()

    @classmethod
    def get_solo(cls):
        if cached_obj := cache.get(cls.__name__):
            return cached_obj
        elif (obj := cls.load()) and obj.pk:
            cache.set(cls.__name__, obj)
        return obj

    def __flush_cache(self):
        cache.delete(self.__class__.__name__)
