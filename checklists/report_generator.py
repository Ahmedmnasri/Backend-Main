"""
PDF Report Generator for Checklist Executions
"""
import os
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class ChecklistReportGenerator:
    """Generate PDF reports for checklist executions."""
    
    def __init__(self, execution):
        self.execution = execution
        self.assignment = execution.assignment
        self.technician = execution.technician
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles for the report."""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        # Header style
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        # Normal style
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
    
    def generate_pdf(self):
        """Generate the PDF report and return the file path."""
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'execution_{self.execution.id}_report_{timestamp}.pdf'
        filepath = os.path.join(reports_dir, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build the story (content)
        story = []
        
        # Title
        story.append(Paragraph("Inspection Report", self.title_style))
        story.append(Spacer(1, 20))
        
        # Report Information
        story.append(Paragraph("Report Information", self.header_style))
        
        report_info = [
            ['Report ID:', f'RPT-{self.execution.id}'],
            ['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Assignment:', self.assignment.title],
            ['Technician:', f'{self.technician.first_name} {self.technician.last_name}' if self.technician.first_name else self.technician.email],
            ['Sector:', self.assignment.sector.name if self.assignment.sector else 'N/A'],
            ['Due Date:', self.assignment.due_date.strftime('%Y-%m-%d') if self.assignment.due_date else 'N/A'],
            ['Completion Date:', self.execution.completed_at.strftime('%Y-%m-%d %H:%M:%S') if self.execution.completed_at else 'In Progress'],
            ['Status:', self.execution.status.title()]
        ]
        
        info_table = Table(report_info, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Systems and Tasks
        story.append(Paragraph("Inspection Results", self.header_style))
        
        # Get task results
        task_results = self.execution.task_results.all().select_related('task', 'task__system')
        
        if task_results:
            # Group by system
            systems_data = {}
            for result in task_results:
                system_name = result.task.system.name
                if system_name not in systems_data:
                    systems_data[system_name] = []
                systems_data[system_name].append(result)
            
            for system_name, results in systems_data.items():
                # System header
                story.append(Paragraph(f"System: {system_name}", self.header_style))
                
                # Tasks table
                task_data = [['Task', 'Status', 'Notes']]
                
                for result in results:
                    status_text = result.status.upper() if result.status else 'PENDING'
                    notes_text = result.notes[:100] + '...' if result.notes and len(result.notes) > 100 else (result.notes or '')
                    
                    task_data.append([
                        result.task.description,
                        status_text,
                        notes_text
                    ])
                
                tasks_table = Table(task_data, colWidths=[3*inch, 1*inch, 2*inch])
                tasks_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP')
                ]))
                
                # Color code status cells
                for i, result in enumerate(results, 1):
                    if result.status == 'ok':
                        tasks_table.setStyle(TableStyle([
                            ('BACKGROUND', (1, i), (1, i), colors.lightgreen)
                        ]))
                    elif result.status == 'not_ok':
                        tasks_table.setStyle(TableStyle([
                            ('BACKGROUND', (1, i), (1, i), colors.lightcoral)
                        ]))
                
                story.append(tasks_table)
                story.append(Spacer(1, 15))
        else:
            story.append(Paragraph("No task results found for this execution.", self.normal_style))
        
        # Summary
        story.append(Paragraph("Summary", self.header_style))
        
        total_tasks = task_results.count()
        ok_tasks = task_results.filter(status='ok').count()
        not_ok_tasks = task_results.filter(status='not_ok').count()
        pending_tasks = total_tasks - ok_tasks - not_ok_tasks
        
        summary_data = [
            ['Total Tasks:', str(total_tasks)],
            ['OK Tasks:', str(ok_tasks)],
            ['Not OK Tasks:', str(not_ok_tasks)],
            ['Pending Tasks:', str(pending_tasks)],
            ['Completion Rate:', f'{(ok_tasks + not_ok_tasks) / total_tasks * 100:.1f}%' if total_tasks > 0 else '0%']
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        
        # Build PDF
        doc.build(story)
        
        return filepath, filename
    
    def get_download_response(self):
        """Generate PDF and return HTTP response for download."""
        filepath, filename = self.generate_pdf()
        
        with open(filepath, 'rb') as pdf_file:
            response = HttpResponse(pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
