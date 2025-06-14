from django.db import models


class InspectionPDF(models.Model):
    """
    Model for storing uploaded PDF files containing inspection checklists.
    """
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='pdfs/', help_text="PDF file upload")
    file_path = models.TextField(blank=True, null=True, help_text="Path to file in Supabase Storage (optional)")
    description = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey(
        'users.SupabaseUser',
        on_delete=models.CASCADE,
        related_name='uploaded_pdfs'
    )
    sector = models.ForeignKey(
        'sectors.Sector',
        on_delete=models.CASCADE,
        related_name='pdfs',
        null=True,
        blank=True
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processing_errors = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'inspection_pdfs'
        ordering = ['-upload_date']
        verbose_name = 'Inspection PDF'
        verbose_name_plural = 'Inspection PDFs'


class InspectionSystem(models.Model):
    """
    Model for equipment systems that have been extracted from PDFs.
    Each system contains multiple task items.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    pdf = models.ForeignKey(
        InspectionPDF,
        on_delete=models.CASCADE,
        related_name='inspection_systems'
    )
    system_number = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'inspection_systems'
        ordering = ['name']
        verbose_name = 'Inspection System'
        verbose_name_plural = 'Inspection Systems'

    @property
    def task_count(self):
        """Return the number of tasks in this system."""
        return self.tasks.count()


class ChecklistTask(models.Model):
    """
    Model for individual inspection tasks extracted from PDFs.
    """
    system = models.ForeignKey(
        InspectionSystem,
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    number = models.IntegerField()  # Task number within the checklist
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.number}. {self.description[:50]}"

    class Meta:
        db_table = 'checklist_tasks'
        ordering = ['system', 'number']
        verbose_name = 'Checklist Task'
        verbose_name_plural = 'Checklist Tasks'


class ChecklistAssignment(models.Model):
    """
    Model for assigning inspection checklists to technicians for specific dates.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    systems = models.ManyToManyField(
        InspectionSystem,
        related_name='assignments',
        through='AssignmentSystem'
    )
    technician = models.ForeignKey(
        'users.SupabaseUser',
        on_delete=models.CASCADE,
        related_name='checklist_assignments'
    )
    assigned_by = models.ForeignKey(
        'users.SupabaseUser',
        on_delete=models.CASCADE,
        related_name='assigned_checklists'
    )
    sector = models.ForeignKey(
        'sectors.Sector',
        on_delete=models.CASCADE,
        related_name='checklist_assignments'
    )
    due_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'checklist_assignments'
        ordering = ['-due_date']
        verbose_name = 'Checklist Assignment'
        verbose_name_plural = 'Checklist Assignments'


class AssignmentSystem(models.Model):
    """
    Through model for the many-to-many relationship between assignments and systems.
    """
    assignment = models.ForeignKey(ChecklistAssignment, on_delete=models.CASCADE)
    system = models.ForeignKey(InspectionSystem, on_delete=models.CASCADE)

    class Meta:
        db_table = 'assignment_systems'
        unique_together = ['assignment', 'system']


class ChecklistExecution(models.Model):
    """
    Model for recording the execution of a checklist assignment.
    """
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('submitted', 'Submitted'),
    ]

    assignment = models.ForeignKey(
        ChecklistAssignment,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    technician = models.ForeignKey(
        'users.SupabaseUser',
        on_delete=models.CASCADE,
        related_name='executions',
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started'
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Execution for: {self.assignment.title}"

    class Meta:
        db_table = 'checklist_executions'
        ordering = ['-completed_at']
        verbose_name = 'Checklist Execution'
        verbose_name_plural = 'Checklist Executions'

    @property
    def progress_percentage(self):
        """Calculate the progress percentage based on completed tasks."""
        total_items = self.task_results.count()
        if total_items == 0:
            return 0
        completed_items = self.task_results.exclude(status='pending').count()
        return int((completed_items / total_items) * 100)


class TaskResult(models.Model):
    """
    Model for recording the results of individual checklist tasks.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('na', 'Not Applicable'),
        ('in_progress', 'In Progress'),
    ]

    execution = models.ForeignKey(
        ChecklistExecution,
        on_delete=models.CASCADE,
        related_name='task_results'
    )
    task = models.ForeignKey(
        ChecklistTask,
        on_delete=models.CASCADE,
        related_name='results'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    notes = models.TextField(blank=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Result for: {self.task}"

    class Meta:
        db_table = 'task_results'
        ordering = ['task__number']
        verbose_name = 'Task Result'
        verbose_name_plural = 'Task Results'
        unique_together = ['execution', 'task']


class TaskPhoto(models.Model):
    """
    Model for storing photos uploaded as evidence for task results.
    """
    task_result = models.ForeignKey(
        TaskResult,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    file_path = models.TextField(help_text="Path to photo in Supabase Storage")
    caption = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for: {self.task_result}"

    class Meta:
        db_table = 'task_photos'
        ordering = ['-uploaded_at']
        verbose_name = 'Task Photo'
        verbose_name_plural = 'Task Photos'