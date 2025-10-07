from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _



class User(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(_('phone'), max_length=15, blank=True, null=True)
    city = models.CharField(_('city'), max_length=100, blank=True, null=True)
    avatar = models.ImageField(_('avatar'), upload_to='users/avatars/', blank=True, null=True)
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Создает и возвращает суперпользователя с email и паролем
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
