from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Add user to moderators group'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to add to moderators group')

    def handle(self, *args, **options):
        User = get_user_model()  # Правильный способ получения модели пользователя
        username = options['username']

        try:
            user = User.objects.get(username=username)
            moderator_group, created = Group.objects.get_or_create(name='moderators')

            user.groups.add(moderator_group)
            self.stdout.write(
                self.style.SUCCESS(f'User {username} added to moderators group successfully')
            )

        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with username {username} does not exist')
            )