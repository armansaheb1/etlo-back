"""Etlo URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls import include
from . import settings
from django.conf.urls.static import static
from main import views as mainviews

urlpatterns = [
    path('api/v1/admin/', admin.site.urls),
    path('api/v1/', include('djoser.urls')),
    path('api/v1/', include('djoser.urls.jwt')),
    path('api/v1/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('api/v1/', include('main.urls')),
    path('api/v1/', include('insurance.urls')),
    path('api/v1/', include('foreignbuy.urls')),
    path('api/v1/adminpanel/', include('adminpanel.urls')),
    path('api/v1/api_auth/', include('rest_framework.urls')),
    path('api/v1/api_auth/', include('drf_social_oauth2.urls',namespace='drf'))
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
