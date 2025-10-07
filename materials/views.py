import stripe
from django.conf import settings
from rest_framework import status, viewsets, generics
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, render
from .models import Payment, Course, Lesson, Subscription
from .permissions import IsModerator, IsOwner
from .serializers import PaymentSerializer, CreatePaymentSerializer, CourseSerializer, LessonSerializer, \
    SubscriptionSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth.decorators import login_required
from .tasks import send_course_update_notification

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
            return Lesson.objects.all()
        else:
            return Lesson.objects.filter(owner=self.request.user)

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


stripe.api_key = settings.STRIPE_SECRET_KEY

@swagger_auto_schema(
    method='post',
    operation_description="Создание платежной сессии для курса",
    request_body=CreatePaymentSerializer,
    responses={
        200: openapi.Response(
            description="Сессия создана успешно",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'session_id': openapi.Schema(type=openapi.TYPE_STRING),
                    'url': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        400: "Ошибка в данных запроса",
        404: "Курс не найден"
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """
    Создает сессию Stripe Checkout для оплаты курса
    """
    serializer = CreatePaymentSerializer(data=request.data)
    if serializer.is_valid():
        course = get_object_or_404(Course, id=serializer.validated_data['course_id'])

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': course.currency.lower(),
                        'product_data': {
                            'name': course.title,
                            'description': course.description,
                        },
                        'unit_amount': int(course.price * 100),  # Конвертируем в центы
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=serializer.validated_data['success_url'],
                cancel_url=serializer.validated_data['cancel_url'],
                customer_email=request.user.email,
                metadata={
                    'course_id': course.id,
                    'user_id': request.user.id
                }
            )

            # Создаем запись о платеже
            Payment.objects.create(
                user=request.user,
                course=course,
                amount=course.price,
                currency=course.currency,
                stripe_payment_intent_id=session.payment_intent,
                status='pending'
            )

            return Response({
                'session_id': session.id,
                'url': session.url
            })

        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    operation_description="Получить историю платежей пользователя",
    responses={200: PaymentSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_history(request):
    """
    Возвращает историю платежей текущего пользователя
    """
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    serializer = PaymentSerializer(payments, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def stripe_webhook(request):
    """
    Эндпоинт для вебхуков Stripe
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return Response({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return Response({'error': 'Invalid signature'}, status=400)

    # Обработка событий
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_payment_success(payment_intent)
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        handle_payment_failure(payment_intent)

    return Response({'success': True})


def handle_payment_success(payment_intent):
    """Обработка успешного платежа"""
    try:
        payment = Payment.objects.get(stripe_payment_intent_id=payment_intent['id'])
        payment.status = 'completed'
        payment.save()
        # Здесь можно добавить логику предоставления доступа к курсу
    except Payment.DoesNotExist:
        pass


def handle_payment_failure(payment_intent):
    """Обработка неудачного платежа"""
    try:
        payment = Payment.objects.get(stripe_payment_intent_id=payment_intent['id'])
        payment.status = 'failed'
        payment.save()
    except Payment.DoesNotExist:
        pass

@login_required
def update_course_materials(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    subscribers_emails = Subscription.objects.filter(
        course=course,
        is_active=True
    ).values_list('user__email', flat=True)

    # Отправляем уведомления асинхронно
    send_course_update_notification.delay(
        course.title,
        list(subscribers_emails)
    )
    return render(request, 'course_updated.html', {'course': course})