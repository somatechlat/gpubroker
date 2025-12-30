"""
Access Control Models - GPUBROKERADMIN Control Plane.

Manages permissions, roles, and access across PODs.
"""
from django.db import models
from django.conf import settings
import uuid


class AdminRole(models.Model):
    """
    Admin roles for GPUBROKERADMIN access control.
    """
    
    class RoleType(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Administrator'
        POD_ADMIN = 'pod_admin', 'POD Administrator'
        POD_OPERATOR = 'pod_operator', 'POD Operator'
        VIEWER = 'viewer', 'Viewer'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    role_type = models.CharField(max_length=50, choices=RoleType.choices)
    description = models.TextField(blank=True)
    permissions = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'admin_roles'
        verbose_name = 'Admin Role'
        verbose_name_plural = 'Admin Roles'
    
    def __str__(self):
        return self.name


class AdminUserRole(models.Model):
    """
    Maps users to admin roles, optionally scoped to specific PODs.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_roles'
    )
    role = models.ForeignKey(AdminRole, on_delete=models.CASCADE, related_name='user_assignments')
    
    # If null, role applies globally; otherwise scoped to specific POD
    pod = models.ForeignKey(
        'pod_management.Pod',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='user_roles'
    )
    
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_roles'
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'admin_user_roles'
        unique_together = [['user', 'role', 'pod']]
        verbose_name = 'Admin User Role'
        verbose_name_plural = 'Admin User Roles'
    
    def __str__(self):
        scope = f" on {self.pod.name}" if self.pod else " (global)"
        return f"{self.user.email}: {self.role.name}{scope}"


class AccessAuditLog(models.Model):
    """
    Audit log for admin access and actions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_audit_logs'
    )
    
    action = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=50)
    resource_id = models.UUIDField(blank=True, null=True)
    
    pod = models.ForeignKey(
        'pod_management.Pod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_access_audit_logs'
        verbose_name = 'Access Audit Log'
        verbose_name_plural = 'Access Audit Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email if self.user else 'Unknown'}: {self.action} at {self.created_at}"
