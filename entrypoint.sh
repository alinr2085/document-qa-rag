#!/bin/sh
set -e

python manage.py migrate --noinput

# Create the admin user on first run (from .env)
python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
U = get_user_model()
u, p = os.environ.get('ADMIN_USERNAME', 'admin'), os.environ.get('ADMIN_PASSWORD', 'admin12345')
if not U.objects.filter(username=u).exists():
    U.objects.create_superuser(u, os.environ.get('ADMIN_EMAIL', 'admin@example.com'), p)
    print('superuser created:', u)
"

# Load the sample documents (skips existing ones)
python manage.py load_sample_data

exec "$@"
