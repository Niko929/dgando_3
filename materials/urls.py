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
      path('create-payment/', views.create_course_payment, name='create-payment'),
      path('payment-status/<str:session_id>/', views.check_payment_status, name='payment-status'),
] + router.urls
