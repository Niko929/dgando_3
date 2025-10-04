from django.urls import path
from rest_framework.routers import DefaultRouter
from materials import views
from materials.views import (CourseViewSet,
                             LessonListAPIView, LessonCreateAPIView, LessonRetrieveAPIView, \
                             LessonUpdateAPIView, LessonDestroyAPIView, SubscriptionViewSet)

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
      path('create-course/', views.create_course_product, name='create_course'),
      path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
      path('payment-success/', views.payment_success, name='payment_success'),
      path('payment-cancel/', views.payment_cancel, name='payment_cancel'),
      path('webhook/', views.stripe_webhook, name='stripe_webhook'),
      path('courses/', views.get_courses, name='get_courses'),
] + router.urls
