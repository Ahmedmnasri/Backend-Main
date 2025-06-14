"""
AI Configuration for PDF Processing
Settings and configuration for AI service integration
"""

import os
from django.conf import settings

# AI Service Configuration
AI_CONFIG = {
    # OpenAI Configuration
    'OPENAI': {
        'API_KEY': os.getenv('OPENAI_API_KEY', ''),
        'MODEL': 'gpt-4-vision-preview',
        'MAX_TOKENS': 4000,
        'TEMPERATURE': 0.1,
        'TIMEOUT': 120,
        'MAX_IMAGES': 5,  # Limit images for cost control
        'IMAGE_QUALITY': 'high',
        'COST_PER_1K_TOKENS': 0.01,  # Approximate cost
    },
    
    # Anthropic Claude Configuration
    'CLAUDE': {
        'API_KEY': os.getenv('ANTHROPIC_API_KEY', ''),
        'MODEL': 'claude-3-5-sonnet-20241022',
        'MAX_TOKENS': 4000,
        'TEMPERATURE': 0.1,
        'TIMEOUT': 120,
        'MAX_TEXT_LENGTH': 50000,  # Character limit for input
        'COST_PER_1K_TOKENS': 0.008,  # Approximate cost
    },
    
    # Google Document AI Configuration
    'GOOGLE': {
        'API_KEY': os.getenv('GOOGLE_CLOUD_API_KEY', ''),
        'PROJECT_ID': os.getenv('GOOGLE_CLOUD_PROJECT_ID', ''),
        'PROCESSOR_ID': os.getenv('GOOGLE_DOCUMENT_AI_PROCESSOR_ID', ''),
        'LOCATION': os.getenv('GOOGLE_CLOUD_LOCATION', 'us'),
        'TIMEOUT': 120,
        'COST_PER_PAGE': 0.0015,  # Approximate cost
    },
    
    # Processing Configuration
    'PROCESSING': {
        'ENABLE_AI': os.getenv('ENABLE_AI_PROCESSING', 'true').lower() == 'true',
        'MIN_CONFIDENCE_THRESHOLD': float(os.getenv('AI_MIN_CONFIDENCE', '0.5')),
        'MAX_PDF_SIZE_MB': int(os.getenv('MAX_PDF_SIZE_MB', '50')),
        'MAX_PAGES': int(os.getenv('MAX_PDF_PAGES', '20')),
        'PROCESSING_TIMEOUT': int(os.getenv('AI_PROCESSING_TIMEOUT', '300')),  # 5 minutes
        'RETRY_ATTEMPTS': int(os.getenv('AI_RETRY_ATTEMPTS', '2')),
        'FALLBACK_TO_LEGACY': os.getenv('AI_FALLBACK_TO_LEGACY', 'true').lower() == 'true',
    },
    
    # Cost Management
    'COST_LIMITS': {
        'DAILY_LIMIT_USD': float(os.getenv('AI_DAILY_COST_LIMIT', '100.0')),
        'MONTHLY_LIMIT_USD': float(os.getenv('AI_MONTHLY_COST_LIMIT', '1000.0')),
        'ENABLE_COST_TRACKING': os.getenv('AI_ENABLE_COST_TRACKING', 'true').lower() == 'true',
    },
    
    # Quality Settings
    'QUALITY': {
        'MIN_SYSTEMS_REQUIRED': int(os.getenv('AI_MIN_SYSTEMS', '1')),
        'MIN_TASKS_PER_SYSTEM': int(os.getenv('AI_MIN_TASKS_PER_SYSTEM', '1')),
        'MAX_SYSTEMS_ALLOWED': int(os.getenv('AI_MAX_SYSTEMS', '50')),
        'MAX_TASKS_PER_SYSTEM': int(os.getenv('AI_MAX_TASKS_PER_SYSTEM', '100')),
    }
}

# Service Priority Order
AI_SERVICE_PRIORITY = [
    'OPENAI',    # Primary - best for complex documents with images
    'CLAUDE',    # Secondary - excellent for text-heavy documents
    'GOOGLE',    # Tertiary - cost-effective for high volume
]

def get_ai_config(service: str = None) -> dict:
    """
    Get AI configuration for a specific service or all services
    
    Args:
        service: Service name (OPENAI, CLAUDE, GOOGLE) or None for all
        
    Returns:
        Configuration dictionary
    """
    if service:
        return AI_CONFIG.get(service.upper(), {})
    return AI_CONFIG

def is_ai_enabled() -> bool:
    """Check if AI processing is enabled"""
    return AI_CONFIG['PROCESSING']['ENABLE_AI']

def get_available_services() -> list:
    """Get list of available AI services based on API keys"""
    available = []
    
    for service in AI_SERVICE_PRIORITY:
        config = AI_CONFIG.get(service, {})
        api_key = config.get('API_KEY', '')
        
        if api_key and len(api_key) > 10:  # Basic validation
            available.append(service)
    
    return available

def estimate_processing_cost(pdf_pages: int, service: str = 'OPENAI') -> float:
    """
    Estimate processing cost for a PDF
    
    Args:
        pdf_pages: Number of pages in PDF
        service: AI service to use
        
    Returns:
        Estimated cost in USD
    """
    service_config = get_ai_config(service)
    
    if service == 'OPENAI':
        # Estimate based on tokens (rough approximation)
        estimated_tokens = pdf_pages * 1000  # ~1000 tokens per page
        cost_per_token = service_config.get('COST_PER_1K_TOKENS', 0.01) / 1000
        return estimated_tokens * cost_per_token
        
    elif service == 'CLAUDE':
        # Similar token-based estimation
        estimated_tokens = pdf_pages * 800  # Claude is more efficient
        cost_per_token = service_config.get('COST_PER_1K_TOKENS', 0.008) / 1000
        return estimated_tokens * cost_per_token
        
    elif service == 'GOOGLE':
        # Page-based pricing
        cost_per_page = service_config.get('COST_PER_PAGE', 0.0015)
        return pdf_pages * cost_per_page
    
    return 0.0

def validate_pdf_for_ai_processing(pdf_path: str) -> tuple[bool, str]:
    """
    Validate if PDF is suitable for AI processing
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        (is_valid, error_message)
    """
    try:
        import os
        
        # Check file exists
        if not os.path.exists(pdf_path):
            return False, "PDF file not found"
        
        # Check file size
        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        max_size = AI_CONFIG['PROCESSING']['MAX_PDF_SIZE_MB']
        
        if file_size_mb > max_size:
            return False, f"PDF too large ({file_size_mb:.1f}MB > {max_size}MB)"
        
        # Check page count if PyMuPDF is available
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            
            max_pages = AI_CONFIG['PROCESSING']['MAX_PAGES']
            if page_count > max_pages:
                return False, f"Too many pages ({page_count} > {max_pages})"
                
        except ImportError:
            # PyMuPDF not available, skip page count check
            pass
        
        return True, "Valid for AI processing"
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"

# Environment variable documentation
ENV_VARS_DOCUMENTATION = """
AI Processing Environment Variables:

# API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_claude_api_key_here
GOOGLE_CLOUD_API_KEY=your_google_api_key_here
GOOGLE_CLOUD_PROJECT_ID=your_google_project_id
GOOGLE_DOCUMENT_AI_PROCESSOR_ID=your_processor_id
GOOGLE_CLOUD_LOCATION=us

# Processing Settings
ENABLE_AI_PROCESSING=true
AI_MIN_CONFIDENCE=0.5
MAX_PDF_SIZE_MB=50
MAX_PDF_PAGES=20
AI_PROCESSING_TIMEOUT=300
AI_RETRY_ATTEMPTS=2
AI_FALLBACK_TO_LEGACY=true

# Cost Management
AI_DAILY_COST_LIMIT=100.0
AI_MONTHLY_COST_LIMIT=1000.0
AI_ENABLE_COST_TRACKING=true

# Quality Settings
AI_MIN_SYSTEMS=1
AI_MIN_TASKS_PER_SYSTEM=1
AI_MAX_SYSTEMS=50
AI_MAX_TASKS_PER_SYSTEM=100
"""

def print_env_vars_help():
    """Print environment variables documentation"""
    print(ENV_VARS_DOCUMENTATION)
