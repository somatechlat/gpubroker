"""
Custom test runner that enables managed=True for all models.

This is necessary because our production models use managed=False
(to work with existing database schema), but tests need Django to
create the tables via migrations.
"""
from django.test.runner import DiscoverRunner


class ManagedModelTestRunner(DiscoverRunner):
    """
    Test runner that sets managed=True on all models before running tests.
    
    This allows Django to create tables for models that normally have
    managed=False in production.
    """
    
    def setup_databases(self, **kwargs):
        """Override to patch models before database setup."""
        from django.apps import apps
        
        # Patch all models to be managed
        for model in apps.get_models():
            model._meta.managed = True
        
        return super().setup_databases(**kwargs)
