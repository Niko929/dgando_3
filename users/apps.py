from django.apps import AppConfig
from django.db.models.signals import post_migrate


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Пользователи'

    def ready(self):
        # Импортируем внутри метода, чтобы избежать циклических импортов
        from django.contrib.auth.models import Group, Permission

        def create_moderator_group(sender, **kwargs):
            """Создает группу модераторов после миграций"""
            group, created = Group.objects.get_or_create(name='moderators')

            if created:
                # Добавляем базовые разрешения
                permissions = Permission.objects.filter(
                    codename__in=['view_course', 'change_course', 'view_lesson', 'change_lesson']
                )
                group.permissions.set(permissions)

        # Подключаем сигнал
        post_migrate.connect(create_moderator_group, sender=self)