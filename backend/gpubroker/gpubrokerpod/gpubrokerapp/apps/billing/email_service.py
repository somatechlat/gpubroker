"""
Billing Email Service - Invoice and payment notification emails.

Uses AWS SES for email delivery.
"""

import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger("gpubroker.billing.email")

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SES_FROM_EMAIL = os.getenv("SES_FROM_EMAIL", "billing@gpubroker.live")


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


class BillingEmailService:
    """
    Service for sending billing-related emails via AWS SES.
    """

    @staticmethod
    def send_invoice_email(
        to_email: str,
        invoice_number: str,
        amount: float,
        currency: str,
        plan_name: str,
        invoice_date: datetime,
        due_date: datetime | None,
        pdf_url: str | None,
        line_items: list,
    ) -> dict[str, Any]:
        """
        Send invoice email to customer.

        Args:
            to_email: Customer email
            invoice_number: Invoice number
            amount: Total amount
            currency: Currency code (USD)
            plan_name: Subscription plan name
            invoice_date: Invoice date
            due_date: Payment due date
            pdf_url: URL to download PDF invoice
            line_items: List of invoice line items

        Returns:
            Dict with send result
        """
        date_str = invoice_date.strftime("%B %d, %Y")
        due_str = due_date.strftime("%B %d, %Y") if due_date else "Due on receipt"

        # Build line items HTML
        items_html = ""
        for item in line_items:
            items_html += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #E5E7EB;">{item.get('description', 'Service')}</td>
                <td style="padding: 12px; border-bottom: 1px solid #E5E7EB; text-align: right;">${item.get('amount', 0):.2f}</td>
            </tr>
            """

        subject = f"Invoice #{invoice_number} from GPUBROKER"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: #F3F4F6; padding: 20px; margin: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #0A0A0A 0%, #1F1F1F 100%); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 28px; font-weight: 700; }}
                .header p {{ margin: 10px 0 0; opacity: 0.8; font-size: 14px; }}
                .content {{ padding: 30px; }}
                .invoice-info {{ display: flex; justify-content: space-between; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #F3F4F6; }}
                .invoice-info div {{ }}
                .label {{ font-size: 12px; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
                .value {{ font-size: 16px; color: #111827; font-weight: 600; }}
                .items-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .items-table th {{ background: #F9FAFB; padding: 12px; text-align: left; font-size: 12px; color: #6B7280; text-transform: uppercase; }}
                .items-table th:last-child {{ text-align: right; }}
                .total-row {{ background: #10B981; color: white; }}
                .total-row td {{ padding: 15px 12px; font-weight: 700; font-size: 18px; }}
                .btn {{ display: inline-block; background: #0A0A0A; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 20px; }}
                .btn:hover {{ background: #1F1F1F; }}
                .footer {{ background: #F9FAFB; padding: 20px; text-align: center; color: #6B7280; font-size: 12px; }}
                .footer a {{ color: #10B981; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>GPUBROKER</h1>
                    <p>Invoice #{invoice_number}</p>
                </div>
                
                <div class="content">
                    <div class="invoice-info">
                        <div>
                            <div class="label">Invoice Date</div>
                            <div class="value">{date_str}</div>
                        </div>
                        <div>
                            <div class="label">Due Date</div>
                            <div class="value">{due_str}</div>
                        </div>
                        <div>
                            <div class="label">Plan</div>
                            <div class="value">{plan_name}</div>
                        </div>
                    </div>
                    
                    <table class="items-table">
                        <thead>
                            <tr>
                                <th>Description</th>
                                <th>Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                            <tr class="total-row">
                                <td>Total</td>
                                <td style="text-align: right;">${amount:.2f} {currency}</td>
                            </tr>
                        </tbody>
                    </table>
                    
                    {f'<a href="{pdf_url}" class="btn">Download PDF Invoice</a>' if pdf_url else ''}
                    
                    <p style="margin-top: 30px; color: #6B7280; font-size: 14px;">
                        Thank you for your business! If you have any questions about this invoice,
                        please contact us at <a href="mailto:billing@gpubroker.live" style="color: #10B981;">billing@gpubroker.live</a>
                    </p>
                </div>
                
                <div class="footer">
                    <p>© 2025 GPUBROKER - All rights reserved.</p>
                    <p><a href="https://gpubroker.live">gpubroker.live</a> | <a href="mailto:support@gpubroker.live">support@gpubroker.live</a></p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        INVOICE #{invoice_number}
        ========================
        
        From: GPUBROKER
        Date: {date_str}
        Due: {due_str}
        Plan: {plan_name}
        
        ITEMS
        -----
        {chr(10).join([f"{item.get('description', 'Service')}: ${item.get('amount', 0):.2f}" for item in line_items])}
        
        TOTAL: ${amount:.2f} {currency}
        
        {f'Download PDF: {pdf_url}' if pdf_url else ''}
        
        Questions? Contact billing@gpubroker.live
        
        © 2025 GPUBROKER
        """

        ses = _get_ses_client()

        if not ses:
            logger.info(f"[Email] Mock: Invoice {invoice_number} for {to_email}")
            return {
                "success": True,
                "message_id": "mock-invoice-email",
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

            logger.info(f"[Email] Invoice {invoice_number} sent to {to_email}")
            return {
                "success": True,
                "message_id": response["MessageId"],
                "to": to_email,
            }

        except Exception as e:
            logger.error(f"[Email] Error sending invoice: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_payment_failed_email(
        to_email: str,
        amount: float,
        currency: str,
        plan_name: str,
        error_message: str,
        retry_url: str,
    ) -> dict[str, Any]:
        """
        Send payment failure notification.

        Args:
            to_email: Customer email
            amount: Failed payment amount
            currency: Currency code
            plan_name: Subscription plan name
            error_message: Payment error message
            retry_url: URL to retry payment

        Returns:
            Dict with send result
        """
        subject = "Payment Failed - Action Required"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: #F3F4F6; padding: 20px; margin: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; }}
                .header {{ background: #EF4444; color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .alert-box {{ background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
                .alert-box p {{ color: #991B1B; margin: 0; }}
                .amount {{ font-size: 32px; font-weight: 700; color: #111827; margin: 20px 0; }}
                .btn {{ display: inline-block; background: #0A0A0A; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; }}
                .footer {{ background: #F9FAFB; padding: 20px; text-align: center; color: #6B7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ Payment Failed</h1>
                </div>
                
                <div class="content">
                    <div class="alert-box">
                        <p><strong>Error:</strong> {error_message}</p>
                    </div>
                    
                    <p>We were unable to process your payment for:</p>
                    <div class="amount">${amount:.2f} {currency}</div>
                    <p style="color: #6B7280;">Plan: {plan_name}</p>
                    
                    <p>Please update your payment method to continue using GPUBROKER services.</p>
                    
                    <a href="{retry_url}" class="btn">Update Payment Method</a>
                    
                    <p style="margin-top: 30px; color: #6B7280; font-size: 14px;">
                        If you believe this is an error, please contact us at 
                        <a href="mailto:billing@gpubroker.live" style="color: #10B981;">billing@gpubroker.live</a>
                    </p>
                </div>
                
                <div class="footer">
                    <p>© 2025 GPUBROKER</p>
                </div>
            </div>
        </body>
        </html>
        """

        ses = _get_ses_client()

        if not ses:
            logger.info(f"[Email] Mock: Payment failed notification for {to_email}")
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

            logger.info(f"[Email] Payment failed notification sent to {to_email}")
            return {"success": True, "message_id": response["MessageId"]}

        except Exception as e:
            logger.error(f"[Email] Error sending payment failed email: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_subscription_confirmed_email(
        to_email: str,
        plan_name: str,
        amount: float,
        currency: str,
        next_billing_date: datetime,
    ) -> dict[str, Any]:
        """
        Send subscription confirmation email.
        """
        next_date_str = next_billing_date.strftime("%B %d, %Y")

        subject = f"Welcome to GPUBROKER {plan_name}!"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: #F3F4F6; padding: 20px; margin: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white; padding: 40px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 28px; }}
                .content {{ padding: 30px; }}
                .plan-box {{ background: #F0FDF4; border: 2px solid #10B981; border-radius: 12px; padding: 25px; text-align: center; margin: 20px 0; }}
                .plan-name {{ font-size: 24px; font-weight: 700; color: #059669; }}
                .plan-price {{ font-size: 36px; font-weight: 700; color: #111827; margin: 10px 0; }}
                .btn {{ display: inline-block; background: #0A0A0A; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; }}
                .footer {{ background: #F9FAFB; padding: 20px; text-align: center; color: #6B7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Subscription Confirmed!</h1>
                </div>
                
                <div class="content">
                    <p>Thank you for subscribing to GPUBROKER!</p>
                    
                    <div class="plan-box">
                        <div class="plan-name">{plan_name}</div>
                        <div class="plan-price">${amount:.2f}/{currency}/mo</div>
                        <p style="color: #6B7280; margin: 0;">Next billing: {next_date_str}</p>
                    </div>
                    
                    <p>You now have access to:</p>
                    <ul style="color: #374151;">
                        <li>GPU marketplace with 20+ providers</li>
                        <li>Real-time price comparison</li>
                        <li>One-click deployment</li>
                        <li>AI-powered recommendations</li>
                    </ul>
                    
                    <a href="https://app.gpubroker.live/dashboard" class="btn">Go to Dashboard</a>
                </div>
                
                <div class="footer">
                    <p>© 2025 GPUBROKER - All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        ses = _get_ses_client()

        if not ses:
            logger.info(f"[Email] Mock: Subscription confirmed for {to_email}")
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

            logger.info(f"[Email] Subscription confirmed sent to {to_email}")
            return {"success": True, "message_id": response["MessageId"]}

        except Exception as e:
            logger.error(f"[Email] Error sending subscription confirmed email: {e}")
            return {"success": False, "error": str(e)}
