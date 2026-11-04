from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RecipientNdaEnterView, RecipientNdaView, SignCredentialView, SigningEnvelopeViewSet, SigningNdaPolicyView
from .webhooks import webhook

router = DefaultRouter()
router.register('envelopes', SigningEnvelopeViewSet, basename='signing-envelope')
urlpatterns = [
    path('', include(router.urls)),
    path('credentials/', SignCredentialView.as_view()),
    path('nda-policy/<str:room_id>/', SigningNdaPolicyView.as_view()),
    path('nda/<str:room_id>/', RecipientNdaView.as_view()),
    path('nda/<str:room_id>/enter/', RecipientNdaEnterView.as_view()),
    path('webhook/', webhook, name='sign-webhook'),
]
