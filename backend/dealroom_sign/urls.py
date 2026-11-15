from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SigningNdaResetView, RecipientNdaEnterView, RecipientNdaView, SignCredentialView, SigningWhoViewedView, SigningSourceView, SigningEnvelopeViewSet, SigningNdaPolicyView
from .webhooks import webhook
from .views import SignatureEmailRetryView, SignatureSignerRevokeView, SignatureRequestListView, SignatureOverviewView, SignatureRequestDetailView, SignaturePageListView, SignaturePageView, SignatureExportView

router = DefaultRouter()
router.register('envelopes', SigningEnvelopeViewSet, basename='signing-envelope')
urlpatterns = [
    path('requests', SignatureRequestListView.as_view()),
    path('requests/<uuid:request_id>/signers/<uuid:signer_id>/revoke-room', SignatureSignerRevokeView.as_view()),
    path('requests/<uuid:request_id>/emails/<uuid:effect_id>/retry', SignatureEmailRetryView.as_view()),
    path('overview', SignatureOverviewView.as_view()),
    path('requests/<uuid:request_id>', SignatureRequestDetailView.as_view()),
    path('requests/<uuid:request_id>/pages', SignaturePageListView.as_view()),
    path('requests/<uuid:request_id>/pages/<int:page>', SignaturePageView.as_view()),
    path('exports', SignatureExportView.as_view()),
    path('', include(router.urls)),
    path('who-viewed/<str:room_id>/', SigningWhoViewedView.as_view()),
    path('sources/<str:room_id>/', SigningSourceView.as_view()),
    path('nda-reset/<str:room_id>/<uuid:workflow_id>/', SigningNdaResetView.as_view()),
    path('credentials/', SignCredentialView.as_view()),
    path('nda-policy/<str:room_id>/', SigningNdaPolicyView.as_view()),
    path('nda/<str:room_id>/', RecipientNdaView.as_view()),
    path('nda/<str:room_id>/enter/', RecipientNdaEnterView.as_view()),
    path('webhook/', webhook, name='sign-webhook'),
]
