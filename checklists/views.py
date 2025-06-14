from rest_framework import viewsets, permissions, status, filters, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import (
    InspectionPDF,
    InspectionSystem,
    ChecklistTask,
    ChecklistAssignment,
    ChecklistExecution,
    TaskResult,
    TaskPhoto
)
from .serializers import (
    InspectionPDFSerializer,
    InspectionSystemSerializer,
    InspectionSystemListSerializer,
    ChecklistTaskSerializer,
    ChecklistAssignmentSerializer,
    ChecklistExecutionSerializer,
    TaskResultSerializer,
    TaskPhotoSerializer
)
from users.permissions import (
    IsAdmin,
    IsSupervisor,
    IsTechnician,
    IsAdminOrSupervisor
)
from .utils import process_inspection_pdf


class InspectionPDFViewSet(viewsets.ModelViewSet):
    """ViewSet for InspectionPDF model operations with file upload support."""
    queryset = InspectionPDF.objects.all()
    serializer_class = InspectionPDFSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['upload_date', 'title']
    ordering = ['-upload_date']  # Default ordering

    # Support multipart/form-data for file uploads
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_permissions(self):
        """
        Custom permissions:
        - Admins and Supervisors can upload, view, and manage PDFs
        - Technicians have read-only access
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'process']:
            permission_classes = [IsAdminOrSupervisor]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter PDFs based on user's role and sector."""
        user = self.request.user

        # Filter by sector
        if user.is_admin:
            return InspectionPDF.objects.all()
        else:
            return InspectionPDF.objects.filter(sector=user.sector)

    def perform_create(self, serializer):
        """Set the uploaded_by and sector fields to the requesting user's values."""
        serializer.save(
            uploaded_by=self.request.user,
            sector=self.request.user.sector
        )

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """
        Manually process a PDF to extract inspection systems and tasks.
        Allows reprocessing if force=true is provided.
        """
        inspection_pdf = self.get_object()
        force_reprocess = request.data.get('force', False)

        # Check if already processed
        if inspection_pdf.processed and not force_reprocess:
            # Return success with existing systems count instead of error
            from .models import InspectionSystem
            systems_count = InspectionSystem.objects.filter(pdf=inspection_pdf).count()
            return Response({
                "detail": "PDF has already been processed.",
                "already_processed": True,
                "systems_count": systems_count,
                "status": "success"
            })

        # Process the PDF (or reprocess if forced)
        success = process_inspection_pdf(inspection_pdf)

        if success:
            from .models import InspectionSystem
            systems_count = InspectionSystem.objects.filter(pdf=inspection_pdf).count()
            return Response({
                "detail": "PDF processed successfully.",
                "already_processed": False,
                "systems_count": systems_count,
                "status": "success"
            })
        else:
            return Response({
                "detail": "Failed to process PDF.",
                "error": inspection_pdf.processing_errors,
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def debug_extraction(self, request, pk=None):
        """
        Debug endpoint to see what the AI is extracting from a PDF.
        This helps troubleshoot AI extraction issues.
        """
        inspection_pdf = self.get_object()

        try:
            # Get the absolute path of the PDF file
            import os
            from django.conf import settings
            from .utils import extract_inspections_from_pdf

            pdf_path = os.path.join(settings.MEDIA_ROOT, inspection_pdf.file.name)

            # Check what AI services are available
            from .ai_config import get_available_services, is_ai_enabled
            from .utils import PYMUPDF_AVAILABLE, AI_PROCESSING_AVAILABLE, CLOUD_FREE_AI_PROCESSING_AVAILABLE, FREE_AI_PROCESSING_AVAILABLE

            available_services = get_available_services()
            ai_enabled = is_ai_enabled()

            # Extract text sample for debugging
            text_sample = ""
            if PYMUPDF_AVAILABLE:
                try:
                    import fitz
                    doc = fitz.open(pdf_path)
                    for page_num in range(min(2, len(doc))):  # First 2 pages
                        page = doc[page_num]
                        text_sample += page.get_text("text")[:1000] + "\n---PAGE BREAK---\n"
                    doc.close()
                except Exception as e:
                    text_sample = f"Error extracting text: {e}"

            # Extract inspections using the same method as processing
            inspections = extract_inspections_from_pdf(pdf_path)

            # Return detailed debug information
            debug_info = {
                "pdf_id": inspection_pdf.id,
                "pdf_title": inspection_pdf.title,
                "pdf_path": pdf_path,
                "ai_enabled": ai_enabled,
                "available_ai_services": available_services,
                "ai_processing_available": AI_PROCESSING_AVAILABLE,
                "cloud_free_ai_available": CLOUD_FREE_AI_PROCESSING_AVAILABLE,
                "free_ai_available": FREE_AI_PROCESSING_AVAILABLE,
                "pymupdf_available": PYMUPDF_AVAILABLE,
                "extraction_method": "AI + Legacy Fallback",
                "total_systems_found": len(inspections),
                "text_sample": text_sample[:2000],  # First 2000 chars for debugging
                "systems": []
            }

            for i, inspection in enumerate(inspections):
                system_info = {
                    "system_number": i + 1,
                    "system_name": inspection.get('name', 'Unknown'),
                    "task_count": len(inspection.get('tasks', [])),
                    "tasks": []
                }

                for j, task in enumerate(inspection.get('tasks', [])):
                    task_info = {
                        "task_number": task.get('number', j + 1),
                        "description": task.get('description', 'No description'),
                        "type": task.get('type', 'inspection')
                    }
                    system_info["tasks"].append(task_info)

                debug_info["systems"].append(system_info)

            return Response({
                "success": True,
                "debug_info": debug_info,
                "message": "Debug extraction completed successfully"
            })

        except Exception as e:
            import traceback
            return Response({
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "message": "Debug extraction failed"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InspectionSystemViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for InspectionSystem model operations (read-only)."""
    queryset = InspectionSystem.objects.all()
    serializer_class = InspectionSystemSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']  # Default ordering

    def get_queryset(self):
        """Filter systems based on user's role and sector."""
        user = self.request.user

        # Base queryset without task_count annotation
        queryset = InspectionSystem.objects.all()

        # Filter by sector
        if not user.is_admin:
            queryset = queryset.filter(pdf__sector=user.sector)

        # Filter by PDF if specified
        pdf_id = self.request.query_params.get('pdf', None)
        if pdf_id:
            queryset = queryset.filter(pdf_id=pdf_id)

        return queryset

    def get_serializer_class(self):
        """Return different serializers based on action."""
        if self.action == 'list':
            return InspectionSystemListSerializer
        return InspectionSystemSerializer


class ChecklistAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet for ChecklistAssignment model operations."""
    queryset = ChecklistAssignment.objects.all()
    serializer_class = ChecklistAssignmentSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'status', 'created_at']
    ordering = ['-due_date']  # Default ordering

    def create(self, request, *args, **kwargs):
        """Override create to add detailed error logging."""
        print(f"Assignment creation request data: {request.data}")
        print(f"Request user: {request.user}")
        print(f"Request user sector: {getattr(request.user, 'sector', 'No sector')}")

        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            print(f"Assignment creation error: {str(e)}")
            print(f"Error type: {type(e)}")
            if hasattr(e, 'detail'):
                print(f"Error detail: {e.detail}")
            raise

    def get_permissions(self):
        """
        Custom permissions:
        - Admins and Supervisors can create, update, and delete assignments
        - Technicians can view their assigned tasks
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminOrSupervisor]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter assignments based on user's role and sector."""
        user = self.request.user

        # Base queryset
        queryset = ChecklistAssignment.objects.all()

        # Filter by sector, role, and status
        if user.is_admin:
            pass  # Admins can see all assignments
        elif user.is_supervisor:
            queryset = queryset.filter(sector=user.sector)
        else:  # Technician
            queryset = queryset.filter(technician=user)

        # Filter by status if specified
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Filter by due date range if specified
        from_date = self.request.query_params.get('from_date', None)
        to_date = self.request.query_params.get('to_date', None)

        if from_date:
            queryset = queryset.filter(due_date__gte=from_date)
        if to_date:
            queryset = queryset.filter(due_date__lte=to_date)

        return queryset

    def perform_create(self, serializer):
        """Set the assigned_by and sector fields to the requesting user's values."""
        serializer.save(
            assigned_by=self.request.user,
            sector=self.request.user.sector
        )

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """
        Get assignments formatted for a calendar view.
        Returns data grouped by date.
        """
        user = request.user

        # Get date range parameters
        from_date = request.query_params.get('from_date', None)
        to_date = request.query_params.get('to_date', None)

        # Filter assignments
        queryset = self.get_queryset()
        if from_date:
            queryset = queryset.filter(due_date__gte=from_date)
        if to_date:
            queryset = queryset.filter(due_date__lte=to_date)

        # Group assignments by date
        calendar_data = {}
        for assignment in queryset:
            date_str = assignment.due_date.isoformat()
            if date_str not in calendar_data:
                calendar_data[date_str] = []

            # Add basic assignment data
            calendar_data[date_str].append({
                'id': assignment.id,
                'title': assignment.title,
                'status': assignment.status,
                'technician_name': assignment.technician.get_full_name(),
                'system_count': assignment.systems.count()
            })

        return Response(calendar_data)


class ChecklistExecutionViewSet(viewsets.ModelViewSet):
    """ViewSet for ChecklistExecution model operations."""
    queryset = ChecklistExecution.objects.all()
    serializer_class = ChecklistExecutionSerializer

    def get_permissions(self):
        """
        Custom permissions:
        - Technicians can update their own executions
        - Supervisors can view executions in their sector
        - Admins can view all executions
        """
        if self.action in ['update', 'partial_update']:
            permission_classes = [permissions.IsAuthenticated]  # Further checks in get_queryset
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter executions based on user's role and sector."""
        user = self.request.user

        # Base queryset with progress calculation
        queryset = ChecklistExecution.objects.all()

        # Add filter logic
        if user.is_admin:
            pass  # Admins can see all executions
        elif user.is_supervisor:
            queryset = queryset.filter(assignment__sector=user.sector)
        else:  # Technician
            queryset = queryset.filter(assignment__technician=user)

        # Filter by status if specified
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset

    @action(detail=True, methods=['post'], url_path='generate-report')
    def generate_report(self, request, pk=None):
        """Generate a PDF report for the execution and save it to the database."""
        from rest_framework.response import Response
        from rest_framework import status
        from django.http import HttpResponse
        from .report_generator import ChecklistReportGenerator
        from reports.models import Report
        from datetime import datetime
        import os
        from django.conf import settings

        try:
            execution = self.get_object()
            print(f"DEBUG: Generating report for execution {execution.id}")

            # Check if execution is completed
            if execution.status != 'completed':
                return Response({
                    'success': False,
                    'message': 'Cannot generate report for incomplete execution'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if a report already exists for this execution
            existing_report = Report.objects.filter(execution=execution).first()
            if existing_report:
                print(f"DEBUG: Report already exists for execution {execution.id}, returning existing report")
                # Return the existing report data
                relative_path = os.path.relpath(existing_report.file_path, settings.MEDIA_ROOT) if existing_report.file_path else None
                file_url = f'/media/{relative_path.replace(os.sep, "/")}' if relative_path else None

                report_data = {
                    'id': f"report_{execution.id}",
                    'execution_id': execution.id,
                    'report_url': file_url,
                    'file_url': file_url,
                    'filename': os.path.basename(existing_report.file_path) if existing_report.file_path else None,
                    'generated_at': existing_report.created_at.isoformat(),
                    'status': 'completed'
                }

                return Response({
                    'success': True,
                    'data': report_data,
                    'message': 'Report already exists'
                }, status=status.HTTP_200_OK)

            # Generate the PDF report
            generator = ChecklistReportGenerator(execution)
            filepath, filename = generator.generate_pdf()

            # Create the URL for accessing the file
            relative_path = os.path.relpath(filepath, settings.MEDIA_ROOT)
            file_url = f'/media/{relative_path.replace(os.sep, "/")}'

            # Create a Report record in the database
            report_title = f"Inspection Report - {execution.assignment.title} - {datetime.now().strftime('%Y-%m-%d')}"
            report = Report.objects.create(
                title=report_title,
                execution=execution,
                generated_by=request.user,
                report_type='pdf',
                file_path=filepath,
                notes=f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )

            print(f"DEBUG: Created Report record with ID {report.id}")

            report_data = {
                'id': f"report_{execution.id}",
                'execution_id': execution.id,
                'report_url': file_url,
                'file_url': file_url,
                'filename': filename,
                'generated_at': report.created_at.isoformat(),
                'status': 'completed',
                'database_id': report.id
            }

            print(f"DEBUG: Report generated successfully: {report_data}")

            return Response({
                'success': True,
                'data': report_data,
                'message': 'Report generated successfully'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"ERROR: Failed to generate report: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        """Custom create method to handle execution creation with minimal response."""
        from rest_framework.response import Response
        from rest_framework import status
        from .models import TaskResult

        try:
            # Use the default creation logic
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Get the assignment from validated data
            assignment = serializer.validated_data.get('assignment')
            print(f"DEBUG: Assignment: {assignment}")

            if assignment:
                print(f"DEBUG: Assignment technician: {assignment.technician}")
                print(f"DEBUG: Assignment systems count: {assignment.systems.count()}")

                # Set the technician from the assignment and save the execution
                execution = serializer.save(technician=assignment.technician)
                print(f"DEBUG: Created execution: {execution.id}")

                # Create task results for all tasks in the assigned systems
                try:
                    task_results_created = 0
                    for system in assignment.systems.all():
                        print(f"DEBUG: Processing system: {system.name} (ID: {system.id})")
                        for task in system.tasks.all():
                            task_result, created = TaskResult.objects.get_or_create(
                                execution=execution,
                                task=task,
                                defaults={'status': 'pending'}
                            )
                            if created:
                                task_results_created += 1
                                print(f"DEBUG: Created TaskResult for task {task.id}")
                            else:
                                print(f"DEBUG: TaskResult already exists for task {task.id}")

                    print(f"DEBUG: Created {task_results_created} TaskResult records")
                except Exception as task_error:
                    print(f"WARNING: Error creating TaskResults: {task_error}")
                    # Don't raise the error - let the execution creation succeed

            else:
                print("DEBUG: No assignment provided, saving without technician")
                execution = serializer.save()

            print(f"DEBUG: Successfully created execution {execution.id}")

            # Return a minimal response to avoid serialization issues
            response_data = {
                'id': execution.id,
                'assignment': execution.assignment.id if execution.assignment else None,
                'technician': execution.technician.id if execution.technician else None,
                'status': execution.status,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'created_at': execution.created_at.isoformat() if execution.created_at else None,
                'notes': execution.notes
            }

            print(f"DEBUG: Returning response data: {response_data}")

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"ERROR in create method: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        """Set the technician field when creating an execution and create TaskResult records."""
        from .models import TaskResult

        try:
            # Get the assignment from validated data
            assignment = serializer.validated_data.get('assignment')
            print(f"DEBUG: Assignment: {assignment}")

            if assignment:
                print(f"DEBUG: Assignment technician: {assignment.technician}")
                print(f"DEBUG: Assignment systems count: {assignment.systems.count()}")

                # Set the technician from the assignment and save the execution
                execution = serializer.save(technician=assignment.technician)
                print(f"DEBUG: Created execution: {execution.id}")

                # Create task results for all tasks in the assigned systems in a separate transaction
                # to avoid interfering with the main execution creation
                try:
                    task_results_created = 0
                    for system in assignment.systems.all():
                        print(f"DEBUG: Processing system: {system.name} (ID: {system.id})")
                        for task in system.tasks.all():
                            task_result, created = TaskResult.objects.get_or_create(
                                execution=execution,
                                task=task,
                                defaults={'status': 'pending'}
                            )
                            if created:
                                task_results_created += 1
                                print(f"DEBUG: Created TaskResult for task {task.id}")
                            else:
                                print(f"DEBUG: TaskResult already exists for task {task.id}")

                    print(f"DEBUG: Created {task_results_created} TaskResult records")
                except Exception as task_error:
                    print(f"WARNING: Error creating TaskResults: {task_error}")
                    # Don't raise the error - let the execution creation succeed

            else:
                print("DEBUG: No assignment provided, saving without technician")
                serializer.save()

        except Exception as e:
            print(f"ERROR in perform_create: {e}")
            import traceback
            traceback.print_exc()
            raise

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Mark an execution as completed.
        This is a special endpoint that allows technicians to complete their executions
        even if they don't have permission to update the assignment status.
        """
        execution = self.get_object()
        user = request.user

        # Security check: only the assigned technician can complete the execution
        if execution.assignment.technician != user and not user.is_admin and not user.is_supervisor:
            return Response({'detail': 'You do not have permission to complete this execution.'},
                          status=status.HTTP_403_FORBIDDEN)

        # Update execution status
        execution.status = 'completed'
        execution.completed_at = timezone.now()
        execution.save()

        # Update assignment status (as a side effect)
        assignment = execution.assignment
        assignment.status = 'completed'
        assignment.save()

        # Return the updated execution with assignment info
        serializer = self.get_serializer(execution)
        response_data = serializer.data
        response_data['assignment_status'] = 'completed'
        response_data['assignment_id'] = assignment.id

        return Response(response_data)


class ChecklistTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for ChecklistTask model operations."""
    queryset = ChecklistTask.objects.all()
    serializer_class = ChecklistTaskSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description']
    ordering_fields = ['number', 'description']
    ordering = ['number']  # Default ordering by task number

    def get_queryset(self):
        """Filter tasks by system if system parameter is provided."""
        queryset = super().get_queryset()
        system_id = self.request.query_params.get('system', None)
        if system_id is not None:
            queryset = queryset.filter(system_id=system_id)
        return queryset


class TaskResultViewSet(viewsets.ModelViewSet):
    """ViewSet for TaskResult model operations."""
    queryset = TaskResult.objects.all()
    serializer_class = TaskResultSerializer

    def get_permissions(self):
        """
        Custom permissions:
        - Technicians can update their own task results
        - Supervisors can view results in their sector
        - Admins can view all results
        """
        if self.action in ['update', 'partial_update']:
            permission_classes = [permissions.IsAuthenticated]  # Further checks in get_queryset
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter task results based on user's role and sector."""
        user = self.request.user

        # Base queryset
        queryset = TaskResult.objects.all()

        # Filter by sector, role, and execution
        if user.is_admin:
            pass  # Admins can see all results
        elif user.is_supervisor:
            queryset = queryset.filter(execution__assignment__sector=user.sector)
        else:  # Technician
            queryset = queryset.filter(execution__assignment__technician=user)

        # Filter by execution if specified
        execution_id = self.request.query_params.get('execution', None)
        if execution_id:
            queryset = queryset.filter(execution_id=execution_id)

        return queryset

    def create(self, request, *args, **kwargs):
        """Custom create method with debug logging for TaskResult creation."""
        from rest_framework.response import Response
        from rest_framework import status

        try:
            print(f"DEBUG TaskResult CREATE: Request data: {request.data}")

            # Use the default creation logic
            serializer = self.get_serializer(data=request.data)
            print(f"DEBUG TaskResult CREATE: Serializer created")

            serializer.is_valid(raise_exception=True)
            print(f"DEBUG TaskResult CREATE: Serializer is valid")

            # Save the task result
            task_result = serializer.save()
            print(f"DEBUG TaskResult CREATE: Successfully created TaskResult {task_result.id}")

            # Return the created task result
            response_data = serializer.data
            print(f"DEBUG TaskResult CREATE: Returning response data")

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"ERROR in TaskResult create method: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """Ensure users can only update their own task results."""
        user = request.user
        instance = self.get_object()

        # Check if this result belongs to the user
        if (not user.is_admin and
            not user.is_supervisor and
            instance.execution.assignment.technician != user):
            raise permissions.PermissionDenied("You can only update your own task results.")

        return super().update(request, *args, **kwargs)


class TaskPhotoViewSet(viewsets.ModelViewSet):
    """ViewSet for TaskPhoto model operations."""
    queryset = TaskPhoto.objects.all()
    serializer_class = TaskPhotoSerializer

    def get_permissions(self):
        """
        Custom permissions:
        - Technicians can add/update photos for their own task results
        - Supervisors and Admins have read-only access
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]  # Further checks in perform_create
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter photos based on user's role and sector."""
        user = self.request.user

        # Base queryset
        queryset = TaskPhoto.objects.all()

        # Filter by sector, role, and task result
        if user.is_admin:
            pass  # Admins can see all photos
        elif user.is_supervisor:
            queryset = queryset.filter(task_result__execution__assignment__sector=user.sector)
        else:  # Technician
            queryset = queryset.filter(task_result__execution__assignment__technician=user)

        # Filter by task result if specified
        task_result_id = self.request.query_params.get('task_result', None)
        if task_result_id:
            queryset = queryset.filter(task_result_id=task_result_id)

        return queryset

    def perform_create(self, serializer):
        """Ensure technicians can only add photos to their own task results."""
        user = self.request.user
        task_result = get_object_or_404(
            TaskResult, pk=self.request.data.get('task_result')
        )

        # Check if this task result belongs to the user
        if (not user.is_admin and
            not user.is_supervisor and
            task_result.execution.assignment.technician != user):
            raise permissions.PermissionDenied("You can only add photos to your own task results.")

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """Ensure technicians can only delete their own photos."""
        user = request.user
        instance = self.get_object()

        # Check if this photo belongs to the user
        if (not user.is_admin and
            not user.is_supervisor and
            instance.task_result.execution.assignment.technician != user):
            raise permissions.PermissionDenied("You can only delete your own photos.")

        return super().destroy(request, *args, **kwargs)