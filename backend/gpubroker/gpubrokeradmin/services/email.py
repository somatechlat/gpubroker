"""
GPUBROKER Email Service

AWS SES email sending for GPUBROKER POD.
"""
import os
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger('gpubroker.email')

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SES_FROM_EMAIL = os.getenv("SES_FROM_EMAIL", "noreply@gpubroker.site")
VENDOR_EMAIL = os.getenv("VENDOR_EMAIL", "admin@gpubroker.site")


def _get_ses_client():
    """Get boto3 SES client with error handling."""
    try:
        import boto3
        return boto3.client("ses", region_name=AWS_REGION)
    except ImportError:
        logger.warning("boto3 not installed, using mock mode")
        return None
    except Exception as e:
        logger.error(f"Failed to create SES client: {e}")
        return None


class EmailService:
    """
    Service for sending emails via AWS SES.
    """
    
    @staticmethod
    def send_payment_receipt(
        to_email: str,
        api_key: str,
        plan: str,
        pod_id: str,
        pod_url: str,
        transaction_id: str,
        order_id: str,
        amount: float,
        payment_provider: str,
        name: str,
        ruc: str,
    ) -> Dict[str, Any]:
        """
        Send comprehensive payment receipt with all transaction and pod details.
        
        Args:
            to_email: Customer email
            api_key: API key for the subscription
            plan: Subscription plan
            pod_id: Pod identifier
            pod_url: Pod URL
            transaction_id: Payment transaction ID
            order_id: Payment order ID
            amount: Payment amount
            payment_provider: Payment provider name
            name: Customer name
            ruc: Customer RUC
            
        Returns:
            Dict with send result
        """
        plan_names = {
            "trial": "Prueba Gratuita",
            "pro": "Profesional",
            "corp": "Corporativo",
            "enterprise": "Enterprise",
        }
        plan_display = plan_names.get(plan, plan.upper())
        date_str = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
        
        subject = f"Recibo de Pago - GPUBROKER #{order_id[:8] if order_id else 'N/A'}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; background: #F3F4F6; padding: 20px; margin: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; }}
                .header {{ background: #0A0A0A; color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .section {{ margin-bottom: 25px; }}
                .section-title {{ font-size: 14px; color: #6B7280; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }}
                .info-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #F3F4F6; }}
                .info-label {{ color: #6B7280; }}
                .info-value {{ font-weight: 600; color: #111827; }}
                .key-box {{ background: #F3F4F6; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 12px; word-break: break-all; margin: 10px 0; }}
                .amount-box {{ background: #10B981; color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0; }}
                .amount-box .amount {{ font-size: 32px; font-weight: bold; }}
                .btn {{ display: inline-block; background: #0A0A0A; color: white; padding: 15px 30px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 20px; }}
                .footer {{ background: #F9FAFB; padding: 20px; text-align: center; color: #6B7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>GPUBROKER</h1>
                    <p style="margin: 10px 0 0; opacity: 0.8;">Recibo de Pago</p>
                </div>
                
                <div class="content">
                    <div class="amount-box">
                        <div style="font-size: 14px; opacity: 0.9;">Total Pagado</div>
                        <div class="amount">${amount:.2f} USD</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">Detalles de la Transaccion</div>
                        <div class="info-row">
                            <span class="info-label">Fecha</span>
                            <span class="info-value">{date_str}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Proveedor</span>
                            <span class="info-value">{payment_provider.upper()}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">ID de Orden</span>
                            <span class="info-value">{order_id or 'N/A'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">ID de Transaccion</span>
                            <span class="info-value">{transaction_id or 'N/A'}</span>
                        </div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">Datos del Cliente</div>
                        <div class="info-row">
                            <span class="info-label">Nombre</span>
                            <span class="info-value">{name or 'N/A'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">RUC</span>
                            <span class="info-value">{ruc or 'N/A'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Email</span>
                            <span class="info-value">{to_email}</span>
                        </div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">Tu Suscripcion</div>
                        <div class="info-row">
                            <span class="info-label">Plan</span>
                            <span class="info-value">{plan_display}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Pod ID</span>
                            <span class="info-value">{pod_id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Tokens Incluidos</span>
                            <span class="info-value">{'10,000' if plan == 'pro' else '5,000'}</span>
                        </div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">Tu API Key</div>
                        <div class="key-box">{api_key}</div>
                        <p style="color: #EF4444; font-size: 12px;">IMPORTANTE: Guarda esta clave. No la compartas con nadie.</p>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">Acceso a tu GPUBROKER POD</div>
                        <div class="key-box">{pod_url}</div>
                        <a href="https://admin.gpubroker.site/activate?key={api_key}" class="btn">
                            Activar mi GPUBROKER POD
                        </a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>© 2025 GPUBROKER - Todos los derechos reservados.</p>
                    <p>Soporte: soporte@gpubroker.site | www.gpubroker.site</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        RECIBO DE PAGO - GPUBROKER
        ================================
        
        TOTAL PAGADO: ${amount:.2f} USD
        
        DETALLES DE LA TRANSACCION
        --------------------------
        Fecha: {date_str}
        Proveedor: {payment_provider.upper()}
        ID de Orden: {order_id or 'N/A'}
        ID de Transaccion: {transaction_id or 'N/A'}
        
        DATOS DEL CLIENTE
        -----------------
        Nombre: {name or 'N/A'}
        RUC: {ruc or 'N/A'}
        Email: {to_email}
        
        TU SUSCRIPCION
        --------------
        Plan: {plan_display}
        Pod ID: {pod_id}
        Tokens: {'10,000' if plan == 'pro' else '5,000'}
        
        TU API KEY
        ----------
        {api_key}
        
        ACCESO A TU POD
        ---------------
        {pod_url}
        
        Activa tu pod: https://admin.gpubroker.site/activate?key={api_key}
        
        ================================
        Guarda este email para tus registros.
        Soporte: soporte@gpubroker.site
        """
        
        ses = _get_ses_client()
        
        if not ses:
            logger.info(f"[Email] Mock: Receipt for {to_email}")
            return {
                "success": True,
                "message_id": "mock-message-id",
                "to": to_email,
                "mock": True,
            }
        
        try:
            response = ses.send_email(
                Source=SES_FROM_EMAIL,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                        "Text": {"Data": text_body, "Charset": "UTF-8"},
                    },
                },
            )
            
            logger.info(f"[Email] Receipt sent to {to_email}, MessageId: {response['MessageId']}")
            return {
                "success": True,
                "message_id": response["MessageId"],
                "to": to_email,
            }
            
        except Exception as e:
            logger.error(f"[Email] Error sending receipt: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def send_vendor_notification(
        customer_email: str,
        customer_name: str,
        customer_ruc: str,
        plan: str,
        pod_id: str,
        amount: float,
        transaction_id: str,
        order_id: str,
        payment_provider: str,
    ) -> Dict[str, Any]:
        """
        Send notification to vendor/admin when a new sale is made.
        """
        plan_names = {
            "trial": "Prueba Gratuita",
            "pro": "Profesional",
            "corp": "Corporativo",
        }
        plan_display = plan_names.get(plan, plan.upper())
        date_str = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
        
        subject = f"Nueva Venta - {plan_display} - ${amount:.2f} USD"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; background: #F3F4F6; padding: 20px; margin: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; }}
                .header {{ background: #10B981; color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .amount-box {{ background: #10B981; color: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 25px; }}
                .amount {{ font-size: 36px; font-weight: bold; }}
                .info-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #F3F4F6; }}
                .info-label {{ color: #6B7280; }}
                .info-value {{ font-weight: 600; color: #111827; }}
                .footer {{ background: #F9FAFB; padding: 20px; text-align: center; color: #6B7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Nueva Venta GPUBROKER</h1>
                </div>
                
                <div class="content">
                    <div class="amount-box">
                        <div style="font-size: 14px; opacity: 0.9;">Ingreso</div>
                        <div class="amount">${amount:.2f} USD</div>
                        <div style="font-size: 14px; margin-top: 5px;">{plan_display}</div>
                    </div>
                    
                    <h3 style="color: #111827; margin-bottom: 15px;">Datos del Cliente</h3>
                    <div class="info-row">
                        <span class="info-label">Nombre</span>
                        <span class="info-value">{customer_name or 'N/A'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Email</span>
                        <span class="info-value">{customer_email}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">RUC</span>
                        <span class="info-value">{customer_ruc or 'N/A'}</span>
                    </div>
                    
                    <h3 style="color: #111827; margin: 25px 0 15px;">Detalles de Transaccion</h3>
                    <div class="info-row">
                        <span class="info-label">Fecha</span>
                        <span class="info-value">{date_str}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Proveedor</span>
                        <span class="info-value">{payment_provider.upper()}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Order ID</span>
                        <span class="info-value">{order_id or 'N/A'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Transaction ID</span>
                        <span class="info-value">{transaction_id or 'N/A'}</span>
                    </div>
                    
                    <h3 style="color: #111827; margin: 25px 0 15px;">Pod Asignado</h3>
                    <div class="info-row">
                        <span class="info-label">Pod ID</span>
                        <span class="info-value">{pod_id}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">URL</span>
                        <span class="info-value">https://{pod_id}.gpubroker.site</span>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Notificacion automatica de GPUBROKER</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        ses = _get_ses_client()
        
        if not ses:
            logger.info(f"[Email] Mock: Vendor notification for {customer_email}")
            return {"success": True, "message_id": "mock", "mock": True}
        
        try:
            response = ses.send_email(
                Source=SES_FROM_EMAIL,
                Destination={"ToAddresses": [VENDOR_EMAIL]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
                },
            )
            
            logger.info(f"[Email] Vendor notification sent, MessageId: {response['MessageId']}")
            return {"success": True, "message_id": response["MessageId"]}
            
        except Exception as e:
            logger.error(f"[Email] Error sending vendor notification: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def send_activation_email(to_email: str, api_key: str, plan: str) -> Dict[str, Any]:
        """Send activation email with API key."""
        subject = "🔑 ¡Activa tu GPUBROKER POD!"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; background: #F3F4F6; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; }}
                h1 {{ color: #111827; }}
                .key-box {{ background: #F3F4F6; padding: 20px; border-radius: 8px; font-family: monospace; margin: 20px 0; word-break: break-all; }}
                .btn {{ display: inline-block; background: #1F1F1F; color: white; padding: 15px 30px; border-radius: 8px; text-decoration: none; font-weight: bold; }}
                .footer {{ margin-top: 30px; color: #6B7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Bienvenido a GPUBROKER</h1>
                <p>Tu suscripción al plan <strong>{plan.upper()}</strong> está lista.</p>
                
                <p>Tu API Key:</p>
                <div class="key-box">{api_key}</div>
                
                <p>Haz click para activar tu GPUBROKER POD:</p>
                <a href="https://admin.gpubroker.site/activate?key={api_key}" class="btn">
                    ⚡ Activar mi GPUBROKER POD
                </a>
                
                <div class="footer">
                    <p>Este email fue enviado porque compraste una suscripción en gpubroker.site</p>
                    <p>Si no fuiste tú, ignora este mensaje.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        ses = _get_ses_client()
        
        if not ses:
            logger.info(f"[Email] Mock: Activation email for {to_email}")
            return {"success": True, "message_id": "mock", "mock": True}
        
        try:
            response = ses.send_email(
                Source=SES_FROM_EMAIL,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
                },
            )
            return {"success": True, "message_id": response["MessageId"]}
        except Exception as e:
            logger.error(f"[Email] Error sending activation email: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def send_pod_ready_email(to_email: str, pod_url: str, plan: str) -> Dict[str, Any]:
        """Send email when GPUBROKER POD is ready."""
        subject = "Tu GPUBROKER POD esta listo"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; background: #F3F4F6; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; }}
                h1 {{ color: #10B981; }}
                .url-box {{ background: #F3F4F6; padding: 20px; border-radius: 8px; font-family: monospace; margin: 20px 0; }}
                .btn {{ display: inline-block; background: #1F1F1F; color: white; padding: 15px 30px; border-radius: 8px; text-decoration: none; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ ¡Tu GPUBROKER POD está activo!</h1>
                <p>Tu agente de GPU está listo para ayudarte.</p>
                
                <p>Accede a tu GPUBROKER Agent:</p>
                <div class="url-box">{pod_url}</div>
                
                <a href="{pod_url}" class="btn">Ir a mi GPUBROKER Agent</a>
                
                <p style="margin-top: 30px; color: #6B7280;">
                    Plan: {plan.upper()}<br>
                    Tokens: 10,000 disponibles
                </p>
            </div>
        </body>
        </html>
        """
        
        ses = _get_ses_client()
        
        if not ses:
            logger.info(f"[Email] Mock: Pod ready email for {to_email}")
            return {"success": True, "message_id": "mock", "mock": True}
        
        try:
            response = ses.send_email(
                Source=SES_FROM_EMAIL,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
                },
            )
            return {"success": True, "message_id": response["MessageId"]}
        except Exception as e:
            logger.error(f"[Email] Error sending pod ready email: {e}")
            return {"success": False, "error": str(e)}
