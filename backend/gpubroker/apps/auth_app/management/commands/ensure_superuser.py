from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Ensures the existence of a superuser for Eye of God administration'

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@gpubroker.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'superadmin123!')
        
        if not User.objects.filter(email=email).exists():
            self.stdout.write(f'Creating superuser {email}...')
            User.objects.create_superuser(
                email=email,
                password=password,
                is_active=True,
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created superuser "{email}"'))
        else:
            self.stdout.write(self.style.WARNING(f'Superuser "{email}" already exists'))

