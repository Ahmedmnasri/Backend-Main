from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .views import (
    InspectionPDFViewSet,
    InspectionSystemViewSet,
    ChecklistTaskViewSet,
    ChecklistAssignmentViewSet,
    ChecklistExecutionViewSet,
    TaskResultViewSet,
    TaskPhotoViewSet
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'pdfs', InspectionPDFViewSet)
router.register(r'systems', InspectionSystemViewSet)
router.register(r'tasks', ChecklistTaskViewSet)
router.register(r'assignments', ChecklistAssignmentViewSet)
router.register(r'executions', ChecklistExecutionViewSet)
router.register(r'task-results', TaskResultViewSet)
router.register(r'photos', TaskPhotoViewSet)

# Define the custom view for the /checklists/{id}/results/ endpoint
@api_view(['GET'])
def checklist_results(request, checklist_id):
    """
    Redirect to the task-results with a filter for the specific execution
    """
    # Redirect to task-results filtered by execution ID
    return Response({"message": "Please use /api/checklists/task-results/?execution={execution_id} instead"}, 
                   status=301)

urlpatterns = [
    # Router generated URLs
    path('', include(router.urls)),
    
    # Custom endpoint for backwards compatibility
    path('<int:checklist_id>/results/', checklist_results, name='checklist-results'),
] 