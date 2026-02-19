"""
Centralized message catalog for GPUBROKER Admin.

All user-facing strings must be retrieved via get_message(code, **kwargs).
"""

from typing import Dict

MESSAGES: Dict[str, str] = {
    # Payment / PayPal
    "paypal.not_configured": "PayPal is not configured. Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET.",
    "paypal.auth_failed": "Failed to authenticate with PayPal.",
    "paypal.create_failed": "Failed to create PayPal order.",
    "paypal.capture_not_completed": "Payment not completed. Status: {status}",
    "paypal.capture_failed": "Failed to capture payment.",
    "paypal.api_error": "PayPal API error: {error}",
    "paypal.order_created": "PayPal order created successfully.",
    # Subscription
    "subscription.created_pending": "Revisa tu email para activar tu GPUBROKER POD",
    "subscription.create_error": "Error creando suscripción: {error}",
    "subscription.api_key_invalid": "API Key inválida o expirada",
    "subscription.already_active": "Suscripción ya está activa o en proceso",
    "subscription.provisioning": "Desplegando tu GPUBROKER POD...",
    # Identity validation
    "validation.ruc.length": "RUC debe tener 13 dígitos",
    "validation.ruc.province": "Código de provincia inválido",
    "validation.cedula.length": "Cédula debe tener 10 dígitos",
    "validation.cedula.province": "Código de provincia inválido",
    "validation.cedula.check_digit": "Dígito verificador inválido",
    "validation.identity.format": "Ingrese RUC (13 dígitos) o Cédula (10 dígitos)",
    "validation.tax_id.required": "{field_name} es requerido para registros desde {country_code}",
    # Mode management
    "mode.invalid": "Modo inválido: {mode}. Debe ser 'sandbox' o 'live'",
    "mode.live_requires_confirm": "Cambiar a MODO LIVE requiere confirm=true",
    # Generic
    "error.not_found": "Recurso no encontrado",
}


def get_message(code: str, **kwargs) -> str:
    """
    Retrieve a message by code and format it with kwargs.
    Falls back to the code itself if missing.
    """
    template = MESSAGES.get(code, code)
    try:
        return template.format(**kwargs)
    except Exception:
        return template
