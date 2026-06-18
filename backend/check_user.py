import os; os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.dev'
import django; django.setup()
from apps.accounts.models import User
u = User.objects.filter(email='admin@example.com').first()
if u:
    print(f'Status: {u.status}')
    print(f'Password valid: {u.check_password("AdminPass123")}')
else:
    print('User not found')
