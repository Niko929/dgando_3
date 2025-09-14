from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = 'Quick setup for moderators group with basic permissions'

    def handle(self, *args, **options):
        # Создаем или получаем группу
        group, created = Group.objects.get_or_create(name='moderators')

        if created:
            self.stdout.write(self.style.SUCCESS('Created moderators group'))
        else:
            self.stdout.write(self.style.WARNING('Moderators group already exists, updating permissions'))

        # Очищаем старые permissions
        group.permissions.clear()

        # Базовые разрешения для модераторов
        permission_codenames = [
            # Стандартные разрешения Django
            'view_user', 'change_user',
            'view_group', 'change_group',
            'view_permission',

            # Добавьте другие модели по мере необходимости
        ]

        # Добавляем разрешения
        added_count = 0
        for codename in permission_codenames:
            try:
                permission = Permission.objects.get(codename=codename)
                group.permissions.add(permission)
                self.stdout.write(f'Added: {codename}')
                added_count += 1
            except Permission.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Permission not found: {codename}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Moderators group setup complete. Added {added_count} permissions.'
            )
        )