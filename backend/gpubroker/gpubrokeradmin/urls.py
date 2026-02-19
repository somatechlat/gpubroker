"""
GPUBROKER Admin URL Configuration

URL patterns for GPUBROKER POD administration.
"""
from django.urls import path
from . import views

app_name = 'gpubrokeradmin'

urlpatterns = [
    # Root
    path('', views.index, name='index'),
    
    # Enrollment flow
    path('checkout/', views.checkout, name='checkout'),
    path('activate/', views.activate, name='activate'),
    
    # Deployment flow
    path('provisioning/', views.provisioning, name='provisioning'),
    path('ready/', views.ready, name='ready'),
    
    # Admin dashboard
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/billing/', views.admin_billing, name='admin_billing'),
    path('admin/customers/', views.admin_customers, name='admin_customers'),
    path('admin/costs/', views.admin_costs, name='admin_costs'),
]
