# Generated by Django 5.0.1 on 2025-06-08 05:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checklists', '0003_alter_checklistassignment_assigned_by_and_more'),
        ('users', '0004_delete_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='checklistexecution',
            name='technician',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='executions', to='users.supabaseuser'),
        ),
    ]
