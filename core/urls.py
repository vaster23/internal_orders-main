from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.home, name='home'),
    path('dashboard/', core_views.dashboard, name='dashboard'),
    path('users/', core_views.users, name='users'),
    path('users/add/', core_views.user_add, name='user_add'),
    path('users/<int:user_id>/edit/', core_views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', core_views.user_delete, name='user_delete'),
    path('platform/onboarding/', core_views.company_onboarding, name='company_onboarding'),
    path('platform/companies/', core_views.platform_companies, name='platform_companies'),
    path('platform/companies/<int:company_id>/toggle-active/', core_views.toggle_company_active, name='toggle_company_active'),
    path('notifications/<int:notification_id>/read/', core_views.mark_notification_read, name='mark_notification_read'),
    path('company-inactive/', core_views.company_inactive, name='company_inactive'),
    path('products/', include('products.urls')),
    path('orders/', include('orders.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

handler403 = 'core.views.custom_403'
handler404 = 'core.views.custom_404'
handler500 = 'core.views.custom_500'