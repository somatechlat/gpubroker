"""
GPUBROKER Admin Views

Django views for serving admin templates.
"""
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods


# ============================================
# ENROLLMENT VIEWS
# ============================================

def checkout(request):
    """Checkout page - plan selection and payment."""
    plan = request.GET.get('plan', 'pro')
    return render(request, 'enrollment/checkout.html', {'plan': plan})


def activate(request):
    """Activation page - enter API key."""
    key = request.GET.get('key', '')
    return render(request, 'enrollment/activate.html', {'prefill_key': key})


# ============================================
# DEPLOYMENT VIEWS
# ============================================

def provisioning(request):
    """Provisioning page - pod deployment progress."""
    key = request.GET.get('key', '')
    return render(request, 'deployment/provisioning.html', {'api_key': key})


def ready(request):
    """Ready page - pod deployed, show URL."""
    pod_url = request.GET.get('pod_url', '')
    return render(request, 'deployment/ready.html', {'pod_url': pod_url})


# ============================================
# ADMIN VIEWS
# ============================================

def admin_login(request):
    """Admin login page."""
    return render(request, 'admin/login.html')


def admin_dashboard(request):
    """Admin dashboard - serves static HTML that loads data via API."""
    return render(request, 'admin/index.html')


def admin_billing(request):
    """Admin billing page."""
    return render(request, 'admin/billing.html')


def admin_customers(request):
    """Admin customers page."""
    return render(request, 'admin/customers.html')


def admin_costs(request):
    """Admin costs page."""
    return render(request, 'admin/costs.html')


# ============================================
# ROOT REDIRECT
# ============================================

def index(request):
    """Root redirect to landing page."""
    return redirect('https://gpubroker.site')
