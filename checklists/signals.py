from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import threading

from .models import InspectionPDF
from .utils import process_inspection_pdf


def process_pdf_in_background(inspection_pdf_id):
    """
    Process a PDF in a background thread to avoid blocking the main thread.
    
    Args:
        inspection_pdf_id: The ID of the InspectionPDF to process.
    """
    from .models import InspectionPDF
    
    try:
        inspection_pdf = InspectionPDF.objects.get(id=inspection_pdf_id)
        process_inspection_pdf(inspection_pdf)
    except Exception as e:
        print(f"Error in background PDF processing: {str(e)}")


@receiver(post_save, sender=InspectionPDF)
def auto_process_pdf(sender, instance, created, **kwargs):
    """
    Automatically process a newly uploaded PDF file in the background.
    Only process newly created PDFs that haven't been processed yet.
    """
    if created and not instance.processed:
        # Use threading for a simple background task system
        # For production, consider using Celery or another task queue
        threading.Thread(
            target=process_pdf_in_background, 
            args=(instance.id,)
        ).start() 