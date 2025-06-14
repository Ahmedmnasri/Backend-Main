from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
import os
import io
import base64
from django.conf import settings
from django.template.loader import render_to_string
import tempfile
from django.core.files import File
from datetime import datetime

from .models import Report
from .serializers import ReportSerializer
from checklists.models import ChecklistExecution
from users.permissions import IsAdminOrSupervisor

# Try to import WeasyPrint, but provide alternatives if it's not available
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    print(f"WeasyPrint not available: {e}")
    WEASYPRINT_AVAILABLE = False
    # Alternative PDF libraries to try
    try:
        import pdfkit
        PDF_ALTERNATIVE = 'pdfkit'
    except ImportError:
        try:
            from fpdf import FPDF
            PDF_ALTERNATIVE = 'fpdf'
        except ImportError:
            PDF_ALTERNATIVE = 'text'

# PDF generation fallback function
def generate_simple_pdf(context, tmp_path):
    """Generate a simple text-based PDF when WeasyPrint is not available"""
    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()

        # Header
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(190, 10, 'Inspection Report', 0, 1, 'C')

        pdf.set_font('Arial', 'B', 12)
        pdf.cell(190, 10, f"Checklist: {context['assignment'].title}", 0, 1)
        pdf.cell(190, 10, f"Technician: {context['technician'].get_full_name()}", 0, 1)
        pdf.cell(190, 10, f"Date: {context['date_generated']}", 0, 1)

        pdf.ln(10)

        # Summary
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(190, 10, 'Summary', 0, 1)

        pdf.set_font('Arial', '', 12)
        pdf.cell(190, 10, f"Total Tasks: {context['total_tasks']}", 0, 1)
        pdf.cell(190, 10, f"OK: {context['ok_tasks']}", 0, 1)
        pdf.cell(190, 10, f"Not OK: {context['not_ok_tasks']}", 0, 1)
        pdf.cell(190, 10, f"N/A: {context['na_tasks']}", 0, 1)

        pdf.ln(10)

        # Systems and Tasks
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(190, 10, 'Inspection Results', 0, 1)

        for system_data in context['systems_with_tasks']:
            system = system_data['system']
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(190, 10, f"System: {system.name}", 0, 1)

            for task_data in system_data['tasks']:
                task = task_data['task']
                result = task_data['result']
                pdf.set_font('Arial', '', 11)
                status_text = result.status.upper()
                pdf.cell(190, 10, f"- {task.description}: {status_text}", 0, 1)

                if result.comment:
                    pdf.set_font('Arial', 'I', 10)
                    pdf.cell(190, 10, f"  Notes: {result.comment}", 0, 1)

            pdf.ln(5)

        # Save PDF
        pdf.output(tmp_path)
        return True
    except Exception as e:
        print(f"FPDF fallback failed: {e}")

        # Last resort: create a text file
        with open(tmp_path, 'w') as f:
            f.write("INSPECTION REPORT\n")
            f.write("=================\n\n")
            f.write(f"Checklist: {context['assignment'].title}\n")
            f.write(f"Technician: {context['technician'].get_full_name()}\n")
            f.write(f"Date: {context['date_generated']}\n\n")

            f.write("SUMMARY\n")
            f.write("=======\n")
            f.write(f"Total Tasks: {context['total_tasks']}\n")
            f.write(f"OK: {context['ok_tasks']}\n")
            f.write(f"Not OK: {context['not_ok_tasks']}\n")
            f.write(f"N/A: {context['na_tasks']}\n\n")

            f.write("INSPECTION RESULTS\n")
            f.write("==================\n\n")

            for system_data in context['systems_with_tasks']:
                system = system_data['system']
                f.write(f"System: {system.name}\n")

                for task_data in system_data['tasks']:
                    task = task_data['task']
                    result = task_data['result']
                    status_text = result.status.upper()
                    f.write(f"- {task.description}: {status_text}\n")

                    if result.comment:
                        f.write(f"  Notes: {result.comment}\n")

                f.write("\n")

        # If text file was created, try to convert it to PDF using a different method
        try:
            # Try to convert text to PDF using reportlab if available
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter

                text_content = open(tmp_path, 'r').read()
                c = canvas.Canvas(tmp_path, pagesize=letter)

                # Split text by lines and add to PDF
                y = 750  # Start from top
                for line in text_content.split('\n'):
                    if line.startswith('='):
                        # Skip separator lines
                        continue
                    if line.endswith(':'):
                        # Add spacing for section headers
                        y -= 10
                    c.drawString(30, y, line)
                    y -= 15
                    if y < 50:
                        # Start a new page
                        c.showPage()
                        y = 750

                c.save()
                return True
            except ImportError:
                # If reportlab is not available, just leave as text file
                return True

        except Exception as inner_e:
            print(f"Final fallback conversion failed: {inner_e}")
            return True  # Return true to continue with text file


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for Report model operations."""
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'notes']
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']  # Default ordering

    def get_permissions(self):
        """
        Custom permissions:
        - Only authenticated users can view reports
        - Only admins and supervisors can create reports through standard endpoints
        - The generate action is available to all authenticated users including technicians
        """
        if self.action == 'generate':
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['create']:
            permission_classes = [IsAdminOrSupervisor]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter reports based on user's role and sector."""
        user = self.request.user

        print(f"Reports API - User: {user.email}, Role: {user.role}, ID: {user.id}")

        # Base queryset
        queryset = Report.objects.all()
        print(f"Total reports in database: {queryset.count()}")

        # Filter by sector and role
        if user.is_admin:
            print("User is admin - showing all reports")
            pass  # Admins can see all reports
        elif user.is_supervisor:
            print(f"User is supervisor - filtering by sector: {user.sector}")
            queryset = queryset.filter(execution__assignment__sector=user.sector)
        else:  # Technician
            print(f"User is technician - filtering by technician: {user}")
            queryset = queryset.filter(execution__assignment__technician=user)

        print(f"Filtered reports count: {queryset.count()}")

        # Debug: Print some report details
        for report in queryset[:5]:  # First 5 reports
            print(f"Report {report.id}: {report.title}, Execution: {report.execution.id}, Technician: {report.execution.assignment.technician.email}")

        # Filter by execution if specified
        execution_id = self.request.query_params.get('execution', None)
        if execution_id:
            queryset = queryset.filter(execution_id=execution_id)
            print(f"Further filtered by execution {execution_id}: {queryset.count()} reports")

        return queryset

    def perform_create(self, serializer):
        """Set the generated_by field to the requesting user."""
        serializer.save(generated_by=self.request.user)

    @action(detail=False, methods=['get'])
    def debug(self, request):
        """Debug endpoint to check reports and related data."""
        from checklists.models import ChecklistExecution, ChecklistAssignment
        from users.models import User

        debug_info = {
            'total_reports': Report.objects.count(),
            'total_executions': ChecklistExecution.objects.count(),
            'total_assignments': ChecklistAssignment.objects.count(),
            'total_users': User.objects.count(),
            'current_user': {
                'id': request.user.id,
                'email': request.user.email,
                'role': request.user.role,
                'sector': request.user.sector.name if request.user.sector else None
            },
            'recent_reports': []
        }

        # Get recent reports with details
        recent_reports = Report.objects.select_related(
            'execution__assignment__technician',
            'execution__assignment__sector',
            'generated_by'
        ).order_by('-created_at')[:5]

        for report in recent_reports:
            debug_info['recent_reports'].append({
                'id': report.id,
                'title': report.title,
                'execution_id': report.execution.id,
                'technician_email': report.execution.assignment.technician.email,
                'technician_id': report.execution.assignment.technician.id,
                'sector': report.execution.assignment.sector.name if report.execution.assignment.sector else None,
                'generated_by': report.generated_by.email,
                'created_at': report.created_at.isoformat()
            })

        return Response(debug_info)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download the report file.
        """
        from django.http import HttpResponse, Http404
        import mimetypes

        report = self.get_object()

        if not report.file_path:
            return Response(
                {"detail": "Report file path not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Use the file_path directly (it should be an absolute path)
        file_path = report.file_path

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Report file not found on disk: {file_path}"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'application/pdf'

        # Read and serve the file
        try:
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type=content_type)
                filename = os.path.basename(file_path)
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
        except Exception as e:
            print(f"ERROR downloading report {report.id}: {e}")
            return Response(
                {"detail": f"Error reading file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generate a new report for a completed checklist execution.
        """
        execution_id = request.data.get('execution')
        report_type = request.data.get('report_type', 'pdf')
        title = request.data.get('title')

        if not execution_id:
            return Response(
                {"detail": "Execution ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            execution = ChecklistExecution.objects.get(pk=execution_id)
        except ChecklistExecution.DoesNotExist:
            return Response(
                {"detail": "Execution not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        if (not request.user.is_admin and
            request.user.sector != execution.assignment.sector and
            request.user != execution.assignment.technician):
            return Response(
                {"detail": "You don't have permission to generate a report for this execution."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if execution is completed
        if execution.status != 'completed':
            return Response(
                {"detail": "Cannot generate a report for an incomplete execution."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get systems and their tasks with results
        systems_with_tasks = []
        tasks_with_results = execution.task_results.all().select_related('task', 'task__system')

        # Group tasks by system
        task_by_system = {}
        for task_result in tasks_with_results:
            system = task_result.task.system
            if system.id not in task_by_system:
                task_by_system[system.id] = {
                    'system': system,
                    'tasks': []
                }

            # Add task with its result
            task_by_system[system.id]['tasks'].append({
                'task': task_result.task,
                'result': task_result
            })

        # Convert dictionary to list for template
        for system_id, data in task_by_system.items():
            systems_with_tasks.append(data)

        # Prepare context for the template
        context = {
            'execution': execution,
            'assignment': execution.assignment,
            'technician': execution.assignment.technician,
            'supervisor': execution.assignment.assigned_by,
            'systems_with_tasks': systems_with_tasks,
            'date_generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_tasks': tasks_with_results.count(),
            'ok_tasks': tasks_with_results.filter(status='ok').count(),
            'not_ok_tasks': tasks_with_results.filter(status='not_ok').count(),
            'na_tasks': tasks_with_results.filter(status='na').count()
        }

        # Create PDF file
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:

                # Try to generate PDF using available method
                if WEASYPRINT_AVAILABLE:
                    # Render HTML template
                    html_string = render_to_string('reports/inspection_report.html', context)

                    # Convert to PDF using WeasyPrint
                    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
                    html.write_pdf(target=tmp.name)
                else:
                    # Use alternative PDF generation method
                    generate_simple_pdf(context, tmp.name)

                tmp.flush()

                # Create report title
                if not title:
                    title = f"Inspection Report - {execution.assignment.title} - {datetime.now().strftime('%Y-%m-%d')}"

                # Create Report object in database
                report = Report.objects.create(
                    title=title,
                    execution=execution,
                    generated_by=request.user,
                    report_type=report_type,
                    notes=f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )

                # Add file to report
                tmp.seek(0)
                file_name = f"report_{execution.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

                # Save the file to the report
                report.file.save(file_name, File(open(tmp.name, 'rb')))

            # Return report data with URL
            serializer = self.get_serializer(report)
            response_data = serializer.data
            response_data['report_url'] = request.build_absolute_uri(report.file.url)

            # Add weasyprint_status
            response_data['weasyprint_status'] = "active" if WEASYPRINT_AVAILABLE else "fallback"



            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"detail": f"Error generating PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )