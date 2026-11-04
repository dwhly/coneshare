from django.urls import path
from . import pages

urlpatterns = [path('', pages.staff), path('room/<slug:slug>', pages.room), path('nda/<str:room_id>', pages.room)]
