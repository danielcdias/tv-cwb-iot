# Generated by Django 2.2.5 on 2019-09-16 12:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('model', '0002_auto_20190908_2251'),
    ]

    operations = [
        migrations.AlterField(
            model_name='controlboardevent',
            name='status_received',
            field=models.CharField(max_length=20),
        ),
    ]
