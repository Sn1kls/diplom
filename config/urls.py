"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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

from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import include, path
from ninja import NinjaAPI

from apps.routers import API_ROUTERS
from config import settings
from mixins.handlers import exception_handlers

api = NinjaAPI(docs_decorator=staff_member_required)

for exc_class, handler in exception_handlers:
    api.add_exception_handler(exc_class, handler)

for api_path, router_class in API_ROUTERS:
    api.add_router(api_path, router_class)


urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("api/", api.urls),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
)

urlpatterns + debug_toolbar_urls()

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
