import json
from django.urls import reverse
import stripe
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from config import settings
from .models import Course, Lesson, Subscription, Payment
from .serializers import CourseSerializer, LessonSerializer, SubscriptionSerializer
from .permissions import IsModerator, IsOwner
from rest_framework.permissions import IsAuthenticated
from .services.stripe_service import StripeService


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_queryset(self):
        if self.request.user.groups.filter(name="moderators").exists():
            return Course.objects.all()
        else:
            return Course.objects.filter(owner=self.request.user)

    def get_permissions(self):
        if self.action == "create":
            self.permission_classes = [IsAuthenticated, ~IsModerator]
        elif self.action in ["update", "partial_update", "retrieve"]:
            self.permission_classes = [IsAuthenticated, IsOwner | IsModerator]
        elif self.action == "destroy":
            self.permission_classes = [IsAuthenticated, IsOwner]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["get"])
    def lessons(self, request, pk=None):
        course = self.get_object()
        lessons = course.lessons.all()
        serializer = LessonSerializer(lessons, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_name='subscribe')
    def subscribe(self, request, pk=None):
        course = self.get_object()
        lessons = course.lessons.all()
        serializer = LessonSerializer(lessons, many=True)
        return Response(serializer.data)

class LessonListAPIView(generics.ListAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.groups.filter(name="moderators").exists():
            return Course.objects.all()
        else:
            return Course.objects.filter(owner=self.request.user)

class LessonCreateAPIView(generics.CreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, ~IsModerator]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class LessonRetrieveAPIView(generics.RetrieveAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwner | IsModerator]

class LessonUpdateAPIView(generics.UpdateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwner | IsModerator]

class LessonDestroyAPIView(generics.DestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwner]

class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user, is_active=True)


stripe_service = StripeService()


@require_http_methods(["POST"])
def create_course_product(request):
    """
    Создание курса и регистрация его в Stripe как продукта
    """
    try:
        data = json.loads(request.body)

        # Создаем курс в нашей базе
        course = Course.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            price=data['price']
        )

        # Создаем продукт и цену в Stripe
        stripe_data = StripeService.create_product_with_price(
            name=course.name,
            description=course.description,
            amount=float(course.price)
        )

        # Сохраняем Stripe IDs в курс
        course.stripe_product_id = stripe_data['product'].id
        course.stripe_price_id = stripe_data['price'].id
        course.save()

        return JsonResponse({
            'course_id': course.id,
            'stripe_product_id': course.stripe_product_id,
            'stripe_price_id': course.stripe_price_id
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["POST"])
def create_checkout_session(request):
    """
    Создание сессии оплаты для курса
    """
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')

        course = get_object_or_404(Course, id=course_id, is_active=True)

        # URL для редиректа после оплаты
        success_url = request.build_absolute_uri(
            reverse('payment_success') + f'?session_id={{CHECKOUT_SESSION_ID}}&course_id={course_id}'
        )
        from audioop import reverse
        cancel_url = request.build_absolute_uri(
            reverse('payment_cancel') + f'?course_id={course_id}'
        )

        # Создаем сессию оплаты в Stripe
        session = StripeService.create_checkout_session(
            price_id=course.stripe_price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'course_id': str(course.id),
                'user_id': str(request.user.id)
            }
        )

        # Сохраняем информацию о платеже
        payment = Payment.objects.create(
            user=request.user,
            course=course,
            stripe_session_id=session.id,
            amount=course.price,
            status='pending'
        )

        return JsonResponse({
            'session_id': session.id,
            'url': session.url,
            'payment_id': payment.id
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def payment_success(request):
    """
    Страница успешной оплаты
    """
    session_id = request.GET.get('session_id')
    course_id = request.GET.get('course_id')

    if session_id:
        try:
            # Получаем информацию о сессии из Stripe
            session = StripeService.retrieve_session(session_id)

            # Обновляем статус платежа
            payment = Payment.objects.get(stripe_session_id=session_id)
            payment.status = 'succeeded'
            payment.stripe_payment_intent_id = session.payment_intent
            payment.save()

            # Здесь можно добавить логику предоставления доступа к курсу
            # Например, добавить курс в профиль пользователя

            context = {
                'course': payment.course,
                'payment': payment
            }

            return JsonResponse({
                'status': 'success',
                'message': 'Оплата прошла успешно!',
                'course_name': payment.course.name,
                'amount': float(payment.amount)
            })

        except Payment.DoesNotExist:
            return JsonResponse({'error': 'Платеж не найден'}, status=400)

    return JsonResponse({'error': 'Неверные параметры'}, status=400)


def payment_cancel(request):
    """
    Страница отмены оплаты
    """
    course_id = request.GET.get('course_id')

    if course_id:
        course = get_object_or_404(Course, id=course_id)

        return JsonResponse({
            'status': 'canceled',
            'message': 'Оплата отменена',
            'course_name': course.name
        })

    return JsonResponse({'error': 'Курс не найден'}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """
    Webhook для обработки событий от Stripe
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)

    # Обрабатываем события
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        try:
            payment = Payment.objects.get(stripe_session_id=session.id)
            payment.status = 'succeeded'
            payment.stripe_payment_intent_id = session.payment_intent
            payment.save()

            # Предоставляем доступ к курсу
            grant_course_access(payment.user, payment.course)

        except Payment.DoesNotExist:
            pass

    elif event['type'] == 'checkout.session.expired':
        session = event['data']['object']

        try:
            payment = Payment.objects.get(stripe_session_id=session.id)
            payment.status = 'expired'
            payment.save()
        except Payment.DoesNotExist:
            pass

    return HttpResponse(status=200)


def grant_course_access(user, course):
    """
    Функция для предоставления доступа к курсу
    """
    # Здесь реализуйте логику предоставления доступа
    # Например, добавление курса в список доступных пользователю
    print(f"Предоставлен доступ к курсу {course.name} для пользователя {user.username}")


def get_courses(request):
    """
    Получение списка доступных курсов
    """
    courses = Course.objects.filter(is_active=True)
    courses_data = []

    for course in courses:
        courses_data.append({
            'id': course.id,
            'name': course.name,
            'description': course.description,
            'price': float(course.price),
            'stripe_price_id': course.stripe_price_id
        })

    return JsonResponse({'courses': courses_data})