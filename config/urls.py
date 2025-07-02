from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """Корневая страница API с описанием доступных endpoints"""
    return JsonResponse({
        "message": "OnlineEdu API",
        "version": "1.0",
        "authentication": {
            "register": "/api/auth/register/",
            "login": "/api/auth/login/",
            "refresh": "/api/auth/refresh/"
        },
        "endpoints": {
            "courses": "/api/courses/",
            "lessons": "/api/lessons/",
            "users": "/api/users/",
            "payments": "/api/payments/",
            "admin": "/admin/"
        },
        "examples": {
            "my_profile": "/api/users/me/",
            "all_courses": "/api/courses/",
            "course_detail": "/api/courses/1/",
            "course_lessons": "/api/courses/1/lessons/",
            "payments_by_course": "/api/payments/?course=1",
            "payments_cash_only": "/api/payments/?payment_method=cash",
            "payments_sorted": "/api/payments/?ordering=-payment_date"
        },
        "auth_header": "Authorization: Bearer <your_access_token>"
    })


urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),
    path('api/', include('lms.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)