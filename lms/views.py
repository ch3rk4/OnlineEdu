from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Course, Lesson
from .serializers import CourseSerializer, CourseDetailSerializer, LessonSerializer


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseSerializer

    @action(detail=True, methods=['get'])
    def lessons(self, request, pk=None):
        """Получить все уроки конкретного курса"""
        course = self.get_object()
        lessons = course.lessons.all()
        serializer = LessonSerializer(lessons, many=True)
        return Response(serializer.data)


# Generic views для уроков
class LessonListCreateView(generics.ListCreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer


class LessonRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer