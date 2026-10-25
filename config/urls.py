"""Project URL configuration."""
from django.contrib import admin
from django.urls import path, include

from shop import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('shop.urls')),
]

handler404 = views.custom_404
