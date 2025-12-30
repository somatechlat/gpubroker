"""
GPUBROKER Admin Authentication Models

JWT-based authentication for the admin dashboard.
"""
import hashlib
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class AdminUserManager(BaseUserManager):
    """Custom manager for AdminUser model."""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', AdminUser.Role.SUPER_ADMIN)
        return self.create_user(email, password, **extra_fields)


class AdminUser(AbstractBaseUser, PermissionsMixin):
    """
    Admin user model for GPUBROKER POD administration.
    
    Roles:
    - super_admin: Full access to all features
    - admin: Standard admin access
    - viewer: Read-only access
    """
    
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        ADMIN = 'admin', 'Admin'
        VIEWER = 'viewer', 'Viewer'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADMIN)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Override groups and user_permissions to avoid clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name='admin_user_set',
        related_query_name='admin_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name='admin_user_set',
        related_query_name='admin_user',
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    objects = AdminUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    class Meta:
        db_table = 'gpubroker_admin_users'
        verbose_name = 'Admin User'
        verbose_name_plural = 'Admin Users'
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    def is_super_admin(self) -> bool:
        return self.role == self.Role.SUPER_ADMIN


class AdminSession(models.Model):
    """
    Admin session tracking for audit and security.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(AdminUser, on_delete=models.CASCADE, related_name='sessions')
    token_hash = models.CharField(max_length=64, db_index=True)
    
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'gpubroker_admin_sessions'
        ordering = ['-created_at']
    
    def is_valid(self) -> bool:
        return (
            self.revoked_at is None and 
            self.expires_at > timezone.now()
        )
    
    def revoke(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=['revoked_at'])


class AdminAuditLog(models.Model):
    """
    Audit log for admin actions.
    """
    class ActionType(models.TextChoices):
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        POD_START = 'pod_start', 'Pod Start'
        POD_STOP = 'pod_stop', 'Pod Stop'
        POD_DESTROY = 'pod_destroy', 'Pod Destroy'
        CONFIG_CHANGE = 'config_change', 'Config Change'
        USER_CREATE = 'user_create', 'User Create'
        USER_UPDATE = 'user_update', 'User Update'
        PAYMENT_REFUND = 'payment_refund', 'Payment Refund'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ActionType.choices)
    
    resource_type = models.CharField(max_length=50, blank=True)
    resource_id = models.CharField(max_length=100, blank=True)
    
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'gpubroker_admin_audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
