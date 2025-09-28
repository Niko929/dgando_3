from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from .models import Course, Lesson, Subscription, Payment
from .serializers import CourseSerializer, LessonSerializer, SubscriptionSerializer
from .permissions import IsModerator, IsOwner
from rest_framework.permissions import IsAuthenticated
from .services import stripe_service
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


@api_view(['POST'])
def create_course_payment(request):
    """Создание платежа для курса через Stripe API"""
    course_id = request.data.get('course_id')
    course = get_object_or_404(Course, id=course_id)

    try:
        # 1. Создаем продукт в Stripe
        product = stripe_service.create_product(
            name=course.title,
            description=course.description[:500]  # ограничение длины
        )

        # 2. Создаем цену
        price = stripe_service.create_price(
            product_id=product['id'],
            amount=float(course.price),
            currency='usd'
        )

        # 3. Создаем сессию оплаты
        success_url = request.build_absolute_uri(
            f'/payment/success/?session_id={{CHECKOUT_SESSION_ID}}'
        )
        cancel_url = request.build_absolute_uri('/payment/cancel/')

        session = stripe_service.create_checkout_session(
            price_id=price['id'],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'course_id': course.id,
                'user_id': request.user.id,
            }
        )

        # Сохраняем в базу
        payment = Payment.objects.create(
            user=request.user,
            course=course,
            stripe_session_id=session['id'],
            stripe_product_id=product['id'],
            stripe_price_id=price['id'],
            amount=course.price,
            currency='usd',
            status='pending'
        )

        return Response({
            'session_id': session['id'],
            'url': session['url'],
            'payment_id': payment.id
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def check_payment_status(request, session_id):
    """Проверка статуса платежа"""
    try:
        session = stripe_service.get_session(session_id)

        payment = Payment.objects.get(stripe_session_id=session_id)
        payment.status = session['payment_status']
        payment.save()

        return Response({
            'status': session['payment_status'],
            'paid': session['payment_status'] == 'paid'
        })

    except Payment.DoesNotExist:
        return Response({'error': 'Payment not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)