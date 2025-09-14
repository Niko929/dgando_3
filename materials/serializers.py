from rest_framework import generics, permissions
from rest_framework import serializers
from .models import Course, Lesson, Subscription


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = [
            'id',
            'title',
            'description',
            'preview_image',
            'price',
            'lessons_count',
            'lessons',  # Добавляем поле с уроками
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class CourseSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    lessons_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'lessons_count']

    def get_lessons_count(self, obj):
        return obj.lessons.count()

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'
        read_only_fields = ['user', 'subscribed_at']


