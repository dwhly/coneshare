from django.urls import include, path
from backend.urls import urlpatterns as base_patterns

urlpatterns = [path('api/v1/dealroom-sign/', include('dealroom_sign.urls')),
               path('signing/', include('dealroom_sign.page_urls')), *base_patterns]
