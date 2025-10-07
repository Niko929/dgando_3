from celery import shared_task
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

User = get_user_model()


@shared_task
def send_course_update_notification(course_title, user_emails):
    """
    Асинхронная рассылка писем об обновлении курса
    """
    subject = f'Обновление курса: {course_title}'
    message = f'Курс "{course_title}" был обновлен. Зайдите на платформу, чтобы ознакомиться с новыми материалами.'

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=user_emails,
            fail_silently=False,
        )
        return f"Уведомления отправлены для {len(user_emails)} пользователей"
    except Exception as e:
        return f"Ошибка при отправке уведомлений: {str(e)}"


@shared_task
def check_inactive_users():
    """
    Проверка и блокировка неактивных пользователей
    """
    one_month_ago = timezone.now() - timedelta(days=30)
    inactive_users = User.objects.filter(
        last_login__lt=one_month_ago,
        is_active=True
    )

    count = inactive_users.count()
    inactive_users.update(is_active=False)

    return f"Заблокировано {count} неактивных пользователей"