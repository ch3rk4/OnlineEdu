from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView
)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """Корневая страница API с описанием доступных endpoints"""
    return JsonResponse({
        "message": "OnlineEdu API",
        "version": "1.0.0",
        "documentation": {
            "swagger": request.build_absolute_uri('/api/docs/'),
            "redoc": request.build_absolute_uri('/api/redoc/'),
            "openapi_schema": request.build_absolute_uri('/api/schema/')
        },
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
            "subscriptions": "/api/subscription/",
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
        "features": [
            "JWT Authentication",
            "YouTube URL Validation",
            "Course Subscriptions",
            "Stripe Payments",
            "Pagination & Filtering",
            "Role-based Access Control"
        ],
        "auth_header": "Authorization: Bearer <your_access_token>"
    })


urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),

    # API endpoints
    path('api/', include('users.urls')),
    path('api/', include('lms.urls')),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)