# Generated by Django 5.0.1 on 2025-05-31 20:28

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Sector',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('code', models.CharField(blank=True, max_length=20, null=True)),
                ('location', models.CharField(blank=True, max_length=255, null=True)),
                ('manager_name', models.CharField(blank=True, max_length=255, null=True)),
                ('manager_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('manager_phone', models.CharField(blank=True, max_length=20, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Sector',
                'verbose_name_plural': 'Sectors',
                'db_table': 'sectors',
                'ordering': ['name'],
            },
        ),
    ]
