# Generated by Django 5.0.1 on 2025-06-01 11:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checklists', '0001_initial'),
        ('sectors', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='inspectionpdf',
            name='file',
            field=models.FileField(default='pdfs/default.pdf', help_text='PDF file upload', upload_to='pdfs/'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='inspectionpdf',
            name='file_path',
            field=models.TextField(blank=True, help_text='Path to file in Supabase Storage (optional)', null=True),
        ),
        migrations.AlterField(
            model_name='inspectionpdf',
            name='sector',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='pdfs', to='sectors.sector'),
        ),
    ]
