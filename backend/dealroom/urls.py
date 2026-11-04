from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, recipient

router = DefaultRouter()
for name, cls in [('rooms', views.RoomViewSet), ('orgs', views.OrgViewSet), ('members', views.MemberViewSet), ('grants', views.GrantViewSet), ('share-links', views.EntryLinkViewSet), ('approvals', views.ApprovalViewSet), ('activity', views.ActivityViewSet), ('drift', views.DriftViewSet), ('operations', views.OperationViewSet), ('copies', views.CopyViewSet), ('agent-keys', views.AgentKeyViewSet), ('file-policies', views.FilePolicyViewSet), ('original-exceptions', views.OriginalExceptionViewSet)]:
    router.register(name, cls, basename='dealroom-' + name)
urlpatterns = [
    path('brand/', views.BrandView.as_view(), name='dealroom-brand'),
    path('recipient/<slug:slug>/challenge/', recipient.RecipientChallengeView.as_view(), name='dealroom-challenge'),
    path('recipient/<slug:slug>/confirm/', recipient.RecipientConfirmView.as_view(), name='dealroom-confirm'),
    path('recipient/<slug:slug>/room/', recipient.RecipientRoomView.as_view(), name='dealroom-recipient-room'),
    path('recipient/<slug:slug>/logout/', recipient.RecipientLogoutView.as_view(), name='dealroom-recipient-logout'),
    path('', include(router.urls)),
]
