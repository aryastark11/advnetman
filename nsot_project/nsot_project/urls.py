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
    path('maintenance/', views.maintenance_view, name='maintenance'),
    path('api/maintenance/action/', views.maintenance_action_api, name='maintenance_action_api'),
    path('api/maintenance/status/', views.maintenance_status_api, name='maintenance_status_api'),
    path('cicd/', views.cicd_view, name='cicd_pipeline'),
    path('api/cicd/run/', views.api_run_cicd, name='api_run_cicd'),
    path('api/cicd/golden-audit/', views.api_golden_audit, name='api_golden_audit'),
    path('api/cicd/telemetry/', views.api_telemetry, name='api_telemetry'),
    path('api/cicd/troubleshoot/', views.api_troubleshoot, name='api_troubleshoot'),
    path('console/', views.device_console_view, name='device_console'),
    path('device/<int:device_id>/console/', views.device_console_view, name='device_console_specific'),
    path('config/change/', views.config_change_view, name='config_change'),
    path('api/device/exec/', views.api_device_exec_cmd, name='api_device_exec_cmd'),
    path('api/cicd/commit-change/', views.api_commit_and_pipeline, name='api_commit_and_pipeline'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
