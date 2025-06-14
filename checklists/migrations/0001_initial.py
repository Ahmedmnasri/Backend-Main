# Generated by Django 5.0.1 on 2025-05-31 20:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sectors', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChecklistAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('due_date', models.DateField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('overdue', 'Overdue'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assigned_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assigned_checklists', to='users.user')),
                ('sector', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checklist_assignments', to='sectors.sector')),
                ('technician', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checklist_assignments', to='users.user')),
            ],
            options={
                'verbose_name': 'Checklist Assignment',
                'verbose_name_plural': 'Checklist Assignments',
                'db_table': 'checklist_assignments',
                'ordering': ['-due_date'],
            },
        ),
        migrations.CreateModel(
            name='AssignmentSystem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='checklists.checklistassignment')),
            ],
            options={
                'db_table': 'assignment_systems',
            },
        ),
        migrations.CreateModel(
            name='ChecklistExecution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('not_started', 'Not Started'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('submitted', 'Submitted')], default='not_started', max_length=20)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='executions', to='checklists.checklistassignment')),
                ('technician', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='executions', to='users.user')),
            ],
            options={
                'verbose_name': 'Checklist Execution',
                'verbose_name_plural': 'Checklist Executions',
                'db_table': 'checklist_executions',
                'ordering': ['-completed_at'],
            },
        ),
        migrations.CreateModel(
            name='InspectionPDF',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('file_path', models.TextField(help_text='Path to file in Supabase Storage')),
                ('description', models.TextField(blank=True, null=True)),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
                ('processed', models.BooleanField(default=False)),
                ('processing_errors', models.TextField(blank=True, null=True)),
                ('sector', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pdfs', to='sectors.sector')),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='uploaded_pdfs', to='users.user')),
            ],
            options={
                'verbose_name': 'Inspection PDF',
                'verbose_name_plural': 'Inspection PDFs',
                'db_table': 'inspection_pdfs',
                'ordering': ['-upload_date'],
            },
        ),
        migrations.CreateModel(
            name='InspectionSystem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('system_number', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('pdf', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inspection_systems', to='checklists.inspectionpdf')),
            ],
            options={
                'verbose_name': 'Inspection System',
                'verbose_name_plural': 'Inspection Systems',
                'db_table': 'inspection_systems',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ChecklistTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.IntegerField()),
                ('description', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('system', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='checklists.inspectionsystem')),
            ],
            options={
                'verbose_name': 'Checklist Task',
                'verbose_name_plural': 'Checklist Tasks',
                'db_table': 'checklist_tasks',
                'ordering': ['system', 'number'],
            },
        ),
        migrations.AddField(
            model_name='checklistassignment',
            name='systems',
            field=models.ManyToManyField(related_name='assignments', through='checklists.AssignmentSystem', to='checklists.inspectionsystem'),
        ),
        migrations.AddField(
            model_name='assignmentsystem',
            name='system',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='checklists.inspectionsystem'),
        ),
        migrations.CreateModel(
            name='TaskResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('pass', 'Pass'), ('fail', 'Fail'), ('na', 'Not Applicable'), ('in_progress', 'In Progress')], default='pending', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='task_results', to='checklists.checklistexecution')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='checklists.checklisttask')),
            ],
            options={
                'verbose_name': 'Task Result',
                'verbose_name_plural': 'Task Results',
                'db_table': 'task_results',
                'ordering': ['task__number'],
                'unique_together': {('execution', 'task')},
            },
        ),
        migrations.CreateModel(
            name='TaskPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_path', models.TextField(help_text='Path to photo in Supabase Storage')),
                ('caption', models.TextField(blank=True, null=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('task_result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='checklists.taskresult')),
            ],
            options={
                'verbose_name': 'Task Photo',
                'verbose_name_plural': 'Task Photos',
                'db_table': 'task_photos',
                'ordering': ['-uploaded_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='assignmentsystem',
            unique_together={('assignment', 'system')},
        ),
    ]
