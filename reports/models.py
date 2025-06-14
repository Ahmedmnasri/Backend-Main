from django.db import models


class Report(models.Model):
    """
    Model for storing generated inspection reports.
    """
    REPORT_TYPES = [
        ('pdf', 'PDF Report'),
        ('excel', 'Excel Report'),
        ('csv', 'CSV Report'),
    ]

    title = models.CharField(max_length=255)
    execution = models.ForeignKey(
        'checklists.ChecklistExecution',
        on_delete=models.CASCADE,
        related_name='reports'
    )
    generated_by = models.ForeignKey(
        'users.SupabaseUser',
        on_delete=models.CASCADE,
        related_name='generated_reports'
    )
    report_type = models.CharField(max_length=10, choices=REPORT_TYPES, default='pdf')
    file_path = models.TextField(help_text="Path to report file in Supabase Storage")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'