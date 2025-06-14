from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from checklists.models import ChecklistAssignment, InspectionSystem, ChecklistExecution
from users.models import SupabaseUser
from sectors.models import Sector


class Command(BaseCommand):
    help = 'Create test assignments for different users'

    def handle(self, *args, **options):
        self.stdout.write("Creating test assignments...")

        # Get or create sector
        sector, created = Sector.objects.get_or_create(
            name='info',
            defaults={
                'description': 'Information Technology Sector',
                'code': 'IT',
                'location': 'Main Building'
            }
        )

        # Get users
        try:
            admin_user = SupabaseUser.objects.filter(role='Admin').first()
            supervisor_user = SupabaseUser.objects.filter(role='Supervisor').first()
            technician_user = SupabaseUser.objects.filter(role='Technician').first()

            if not technician_user:
                self.stdout.write(self.style.ERROR("No technician user found"))
                return

            if not supervisor_user:
                self.stdout.write(self.style.ERROR("No supervisor user found"))
                return

            # Get existing systems from the database
            systems = InspectionSystem.objects.all()
            if not systems.exists():
                self.stdout.write(self.style.ERROR("No inspection systems found. Please upload and process a PDF first."))
                return

            system = systems.first()  # Use the first available system

            # Create test assignments for the current week
            today = date.today()
            
            assignments_data = [
                {
                    'title': 'Daily Equipment Check - Monday',
                    'description': 'Routine daily inspection of equipment systems',
                    'due_date': today,
                    'status': 'pending'
                },
                {
                    'title': 'Weekly Safety Inspection',
                    'description': 'Comprehensive weekly safety check',
                    'due_date': today + timedelta(days=1),
                    'status': 'pending'
                },
                {
                    'title': 'Monthly Maintenance Review',
                    'description': 'Monthly review of all maintenance activities',
                    'due_date': today + timedelta(days=2),
                    'status': 'pending'
                }
            ]

            created_count = 0
            for assignment_data in assignments_data:
                assignment, created = ChecklistAssignment.objects.get_or_create(
                    title=assignment_data['title'],
                    defaults={
                        'description': assignment_data['description'],
                        'technician': technician_user,
                        'assigned_by': supervisor_user,
                        'sector': sector,
                        'due_date': assignment_data['due_date'],
                        'status': assignment_data['status']
                    }
                )
                
                if created:
                    # Add the system to the assignment
                    assignment.systems.add(system)
                    
                    # Create execution for the assignment
                    execution, exec_created = ChecklistExecution.objects.get_or_create(
                        assignment=assignment,
                        defaults={
                            'technician': technician_user,
                            'status': 'not_started'
                        }
                    )
                    
                    created_count += 1
                    self.stdout.write(f"Created assignment: {assignment.title}")

            self.stdout.write(
                self.style.SUCCESS(f"Successfully created {created_count} test assignments")
            )

            # Show summary
            total_assignments = ChecklistAssignment.objects.count()
            self.stdout.write(f"Total assignments in database: {total_assignments}")
            
            # Show assignments by user
            for user in SupabaseUser.objects.filter(role='Technician'):
                user_assignments = ChecklistAssignment.objects.filter(technician=user).count()
                self.stdout.write(f"Assignments for {user.email}: {user_assignments}")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creating test assignments: {str(e)}")
            )
