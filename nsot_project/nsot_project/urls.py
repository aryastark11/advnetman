from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from automation import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard_view, name='dashboard'),
    path('device/add/', views.add_device_view, name='add_device'),
    path('device/<int:device_id>/', views.device_detail_view, name='device_detail'),
    path('device/<int:device_id>/edit/', views.edit_device_view, name='edit_device'),
    path('device/<int:device_id>/delete/', views.delete_device_view, name='delete_device'),
    path('device/<int:device_id>/pull-config/', views.pull_device_config_view, name='pull_device_config'),
    path('device/<int:device_id>/save-golden/', views.save_golden_config_view, name='save_golden_config'),
    path('devices/pull-all/', views.pull_all_configs_view, name='pull_all_configs'),
    path('golden-configs/', views.golden_configs_list_view, name='golden_configs'),
    path('templates/', views.templates_list_view, name='templates_list'),
    path('templates/render/', views.render_template_view, name='render_template'),
    path('api/devices/', views.api_devices_view, name='api_devices'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
