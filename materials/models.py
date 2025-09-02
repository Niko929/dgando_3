from django.db import models

# Create your models here.
from django.db import models
from django.utils.translation import gettext_lazy as _


class Course(models.Model):
    objects = None
    title = models.CharField(_('title'), max_length=255)
    preview = models.ImageField(_('preview'), upload_to='courses/previews/', blank=True, null=True)
    description = models.TextField(_('description'), blank=True)

    class Meta:
        verbose_name = _('course')
        verbose_name_plural = _('courses')

    def __str__(self):
        return self.title


class Lesson(models.Model):
    objects = None
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name=_('course')
    )
    title = models.CharField(_('title'), max_length=255)
    description = models.TextField(_('description'), blank=True)
    preview = models.ImageField(_('preview'), upload_to='lessons/previews/', blank=True, null=True)
    video_url = models.URLField(_('video URL'), blank=True)

    class Meta:
        verbose_name = _('lesson')
        verbose_name_plural = _('lessons')

    def __str__(self):
        return self.title