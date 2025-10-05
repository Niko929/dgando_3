from django.urls import path
from rest_framework.routers import DefaultRouter
from materials import views
from materials.views import (CourseViewSet,
                             LessonListAPIView, LessonCreateAPIView, LessonRetrieveAPIView, \
                             LessonUpdateAPIView, LessonDestroyAPIView, SubscriptionViewSet, create_checkout_session,
                             payment_history, stripe_webhook)

app_name = 'materials'

router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')

urlpatterns = [
      path('lessons/', LessonListAPIView.as_view(), name='lesson-list'),
      path('lessons/create/', LessonCreateAPIView.as_view(), name='lesson-create'),
      path('lessons/<int:pk>/', LessonRetrieveAPIView.as_view(), name='lesson-detail'),
      path('lessons/<int:pk>/update/', LessonUpdateAPIView.as_view(), name='lesson-update'),
      path('lessons/<int:pk>/delete/', LessonDestroyAPIView.as_view(), name='lesson-delete'),
      path('subscriptions', SubscriptionViewSet.as_view({'get': 'list'}), name='subscriptions'),
      path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
      path('history/', payment_history, name='payment-history'),
      path('webhook/', stripe_webhook, name='stripe-webhook')
] + router.urls
