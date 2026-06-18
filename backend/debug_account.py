import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.test'
django.setup()
from django.test.utils import setup_test_environment
setup_test_environment()
from rest_framework.test import APIClient
from django.urls import reverse

client = APIClient()
client.post(reverse('auth-register'), {'email':'admin@test.com','password':'Pass1234','company_name':'Test'}, format='json')
resp = client.post(reverse('auth-login'), {'email':'admin@test.com','password':'Pass1234'}, format='json')
h = {
    'HTTP_AUTHORIZATION': f'Bearer {resp.data["access"]}',
    'HTTP_X_TENANT_ID': str(resp.data['active_tenant']['id'])
}

p = client.post(reverse('account-list'), {'name':'Assets','type':'Asset'}, format='json', **h).data
print('parent:', p)

c = client.post(reverse('account-list'), {'name':'Cash','type':'Asset','parent_id':p['id']}, format='json', **h).data
print('child:', c)

from apps.accounting.models import Account
acct = Account.objects.get(pk=c['id'])
print(f'parent_id column: {acct.parent_id}')
print(f'parent attr: {acct.parent}')
