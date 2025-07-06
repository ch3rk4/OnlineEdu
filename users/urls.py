from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserViewSet,
    PaymentViewSet,
    UserRegistrationView,
    CustomTokenObtainPairView
)
from .stripe_views import (
    CreateStripePaymentView,
    StripePaymentStatusView,
    StripeWebhookView,
    UserStripePaymentsView
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    # JWT аутентификация
    path('auth/register/', UserRegistrationView.as_view(), name='user-register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Stripe платежи
    path('payments/stripe/create/', CreateStripePaymentView.as_view(), name='stripe-payment-create'),
    path('payments/stripe/<int:payment_id>/status/', StripePaymentStatusView.as_view(), name='stripe-payment-status'),
    path('payments/stripe/my/', UserStripePaymentsView.as_view(), name='user-stripe-payments'),
    path('payments/stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),

    # API роуты
    path('', include(router.urls)),
]