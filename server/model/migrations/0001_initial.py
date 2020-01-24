import os

from django.db import migrations
from django.contrib.auth.models import User


def generate_superuser(apps, schema_editor):
    django_su_name = os.environ.get('IOT_DJANGO_SU_USER', 'admin')
    django_su_email = os.environ.get('IOT_DJANGO_SU_EMAIL', 'admin@admin.com')
    django_su_pass = os.environ.get('IOT_DJANGO_SU_PASS', 'admin')

    superuser = User.objects.create_superuser(
        username=django_su_name,
        email=django_su_email,
        password=django_su_pass)

    superuser.save()


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.RunPython(generate_superuser),
    ]
