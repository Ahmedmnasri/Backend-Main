from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import action
from django.db.models import Count, Q, QuerySet
import logging
from typing import Type, Union, List

from .models import Sector
from .serializers import SectorSerializer, SectorListSerializer
from users.permissions import IsAdmin, IsAdminOrSupervisor

from users.models import SupabaseUser as User

# Set up logging
logger = logging.getLogger(__name__)


class SectorViewSet(viewsets.ModelViewSet):
    """ViewSet for Sector model operations."""
    serializer_class: Type[SectorSerializer] = SectorSerializer
    permission_classes = [permissions.AllowAny]  # Allow any for production testing
    lookup_field = 'id'
    queryset = Sector.objects.all()  # Default queryset, will be filtered in get_queryset

    def get_permissions(self) -> List[permissions.BasePermission]:
        """
        Custom permissions:
        - Allow any for testing (temporarily)
        - Admins can perform all actions
        - Supervisors can view their sector and update it
        - Technicians can view their sector (read-only)
        """
        # Temporarily allow any for testing
        return [permissions.AllowAny()]

    def get_queryset(self) -> QuerySet[Sector]:
        """Get sectors based on user role and sector access."""
        try:
            user = self.request.user

            if not user.is_authenticated:
                logger.warning("Unauthenticated user attempting to access sectors - allowing for testing")
                return Sector.objects.all().order_by('name')  # Allow all sectors for testing

            # Admin can see all sectors
            if hasattr(user, 'role') and user.role == 'Admin':
                logger.info(f"Admin user accessing all sectors")
                return Sector.objects.all().order_by('name')

            # Supervisor can only see their own sector
            elif hasattr(user, 'role') and user.role == 'Supervisor' and hasattr(user, 'sector') and user.sector:
                logger.info(f"Supervisor user accessing their sector: {user.sector.name}")
                return Sector.objects.filter(id=user.sector.id).order_by('name')

            # Technician can see their sector (read-only)
            elif hasattr(user, 'role') and user.role == 'Technician' and hasattr(user, 'sector') and user.sector:
                logger.info(f"Technician user accessing their sector: {user.sector.name}")
                return Sector.objects.filter(id=user.sector.id).order_by('name')

            logger.warning(f"User without proper role/sector access: {user}")
            return Sector.objects.none()

        except Exception as e:
            logger.error(f"Error in SectorViewSet.get_queryset: {str(e)}")
            return Sector.objects.none()

    def get_serializer_class(self) -> Union[Type[SectorListSerializer], Type[SectorSerializer]]:
        """Return different serializers based on action."""
        if self.action == 'list':
            return SectorListSerializer
        return SectorSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create sector with better error handling"""
        try:
            sector_name = request.data.get('name', 'Unknown')
            print(f"🆕 Creating new sector: {sector_name}")

            # Check for duplicate names
            if Sector.objects.filter(name=sector_name).exists():
                print(f"❌ Sector with name '{sector_name}' already exists")
                return Response(
                    {"error": f"A sector with the name '{sector_name}' already exists"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            response = super().create(request, *args, **kwargs)

            if response.status_code == 201:
                print(f"✅ Sector created successfully: {sector_name}")

            return response

        except Exception as e:
            logger.error(f"Error creating sector: {str(e)}")
            print(f"❌ Error creating sector: {str(e)}")
            return Response(
                {"error": "Failed to create sector. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """Update sector with better error handling"""
        try:
            # Get sector ID from URL parameters (try both 'pk' and 'id')
            sector_id = kwargs.get('pk') or kwargs.get('id') or self.kwargs.get('pk') or self.kwargs.get('id')
            sector_name = request.data.get('name', 'Unknown')
            print(f"✏️ Updating sector {sector_id}: {sector_name}")

            # Check if sector exists
            try:
                sector = Sector.objects.get(id=sector_id)
                print(f"✅ Found sector to update: {sector.name}")
            except Sector.DoesNotExist:
                print(f"❌ Sector with ID {sector_id} not found")
                return Response(
                    {"error": f"Sector with ID {sector_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check for duplicate names (excluding current sector)
            if request.data.get('name') and Sector.objects.filter(name=sector_name).exclude(id=sector_id).exists():
                print(f"❌ Another sector with name '{sector_name}' already exists")
                return Response(
                    {"error": f"Another sector with the name '{sector_name}' already exists"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            response = super().update(request, *args, **kwargs)

            if response.status_code == 200:
                print(f"✅ Sector updated successfully: {sector_name}")

            return response

        except Exception as e:
            logger.error(f"Error updating sector: {str(e)}")
            print(f"❌ Error updating sector: {str(e)}")
            return Response(
                {"error": "Failed to update sector. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """Delete sector with better error handling"""
        try:
            # Get sector ID from URL parameters (try both 'pk' and 'id')
            sector_id = kwargs.get('pk') or kwargs.get('id') or self.kwargs.get('pk') or self.kwargs.get('id')
            print(f"🗑️ Attempting to delete sector with ID: {sector_id}")
            print(f"🔍 Debug - args: {args}, kwargs: {kwargs}")
            print(f"🔍 Debug - self.kwargs: {getattr(self, 'kwargs', 'Not available')}")

            if not sector_id:
                print(f"❌ No sector ID provided in request")
                return Response(
                    {"error": "Sector ID is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if sector exists
            try:
                sector = Sector.objects.get(id=sector_id)
                print(f"✅ Found sector to delete: {sector.name}")

                # Check if sector has users assigned
                user_count = User.objects.filter(sector=sector).count()
                if user_count > 0:
                    print(f"⚠️ Sector {sector.name} has {user_count} users assigned")
                    return Response(
                        {"error": f"Cannot delete sector '{sector.name}' because it has {user_count} users assigned. Please reassign users first."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            except Sector.DoesNotExist:
                print(f"❌ Sector with ID {sector_id} not found in database")
                print(f"📋 Available sector IDs:")
                for s in Sector.objects.all():
                    print(f"   - {s.id} ({s.name})")
                return Response(
                    {"error": f"Sector with ID {sector_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Proceed with deletion
            response = super().destroy(request, *args, **kwargs)

            if response.status_code == 204:
                print(f"✅ Sector deleted successfully: {sector.name}")

            return response

        except Exception as e:
            logger.error(f"Error deleting sector: {str(e)}")
            print(f"❌ Error deleting sector: {str(e)}")
            return Response(
                {"error": "Failed to delete sector. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def list(self, request, *args, **kwargs):
        """Override list to handle errors gracefully"""
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error listing sectors: {str(e)}")
            return Response(
                {"error": "Failed to retrieve sectors. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def users(self, request: Request, pk=None) -> Response:
        """Get all users belonging to a specific sector."""
        try:
            sector = self.get_object()

            # Import here to avoid circular imports
            from users.serializers import UserSerializer

            users = User.objects.filter(sector=sector)
            serializer = UserSerializer(users, many=True)

            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error in users action: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def summary(self, request: Request) -> Response:
        """Get a summary of all sectors with basic stats."""
        try:
            sectors = self.get_queryset()

            # Use the model properties instead of the annotations for calculating totals
            total_sectors = sectors.count()
            total_users = sum(sector.user_count for sector in sectors)
            total_technicians = sum(sector.technician_count for sector in sectors)
            total_supervisors = sum(sector.supervisor_count for sector in sectors)

            # Prepare response
            data = {
                'total_sectors': total_sectors,
                'total_users': total_users,
                'total_technicians': total_technicians,
                'total_supervisors': total_supervisors,
                'sectors': SectorListSerializer(sectors, many=True).data
            }

            return Response(data)
        except Exception as e:
            logger.error(f"Error in summary action: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)