"""
AI Processing Schemas for PDF Document Understanding
Defines the exact JSON structure that AI services should return
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
import json
from enum import Enum

# Enums for better validation
class TaskType(str, Enum):
    inspection = "inspection"
    maintenance = "maintenance"
    safety = "safety"
    startup = "startup"
    shutdown = "shutdown"

class QualityLevel(str, Enum):
    excellent = "excellent"
    good = "good"
    fair = "fair"
    poor = "poor"

class TaskSchema(BaseModel):
    """Schema for individual inspection tasks"""
    number: Optional[int] = Field(None, description="Sequential task number (1, 2, 3, etc.)")
    description: str = Field(..., min_length=10, max_length=500, description="Clear task description")
    type: TaskType = Field(default=TaskType.inspection, description="Task type")
    requirements: Optional[str] = Field(None, description="Special requirements or tools needed")
    safety_notes: Optional[str] = Field(None, description="Safety considerations for this task")
    estimated_time: Optional[int] = Field(None, description="Estimated time in minutes")

    @validator('description')
    def validate_description(cls, v):
        if len(v.strip()) < 10:
            raise ValueError('Task description must be at least 10 characters')
        return v.strip()

class SystemSchema(BaseModel):
    """Schema for equipment/system definitions"""
    name: str = Field(..., min_length=3, max_length=200, description="System or equipment name")
    description: Optional[str] = Field(None, description="Detailed system description")
    category: Optional[str] = Field(None, description="Equipment category")
    location: Optional[str] = Field(None, description="Physical location or area")
    manufacturer: Optional[str] = Field(None, description="Equipment manufacturer")
    model: Optional[str] = Field(None, description="Model number or identifier")
    tasks: List[TaskSchema] = Field(..., description="List of inspection tasks for this system")

    @validator('name')
    def validate_name(cls, v):
        return v.strip()

    @validator('tasks')
    def validate_tasks(cls, v):
        if not v:
            raise ValueError('System must have at least one task')
        for i, task in enumerate(v, 1):
            task.number = i
        return v

class DocumentMetadata(BaseModel):
    """Metadata extracted from the document"""
    title: Optional[str] = Field(None, description="Document title")
    document_type: Optional[str] = Field(None, description="Type of inspection document")
    facility: Optional[str] = Field(None, description="Facility or plant name")
    department: Optional[str] = Field(None, description="Department or area")
    revision: Optional[str] = Field(None, description="Document revision number")
    date: Optional[str] = Field(None, description="Document date")
    author: Optional[str] = Field(None, description="Document author")
    approval: Optional[str] = Field(None, description="Approval information")

class AIExtractionResult(BaseModel):
    success: bool = Field(..., description="Whether extraction was successful")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence score")
    processing_method: str = Field(..., description="AI service used")
    metadata: Optional[DocumentMetadata] = Field(None, description="Document metadata")
    systems: List[SystemSchema] = Field(..., description="Extracted systems and equipment")
    total_systems: int = Field(..., description="Total number of systems found")
    total_tasks: int = Field(..., description="Total number of tasks across all systems")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    extraction_quality: Optional[QualityLevel] = Field(None, description="Quality assessment")
    warnings: Optional[List[str]] = Field(None, description="Any warnings during processing")

    @validator('systems')
    def validate_systems(cls, v):
        if not v:
            raise ValueError('At least one system must be extracted')
        return v

    @validator('total_systems', always=True)
    def validate_total_systems(cls, v, values):
        return len(values.get('systems', []))

    @validator('total_tasks', always=True)
    def validate_total_tasks_count(cls, v, values):
        return sum(len(system.tasks) for system in values.get('systems', []))
    
    @validator('total_tasks')
    def validate_total_tasks(cls, v, values):
        """Ensure total_tasks matches actual task count"""
        if 'systems' in values:
            actual_count = sum(len(system.tasks) for system in values['systems'])
            if v != actual_count:
                return actual_count
        return v

# AI Prompt Templates
AI_EXTRACTION_PROMPT = """
You are reading an inspection checklist PDF. Your task is to extract structured data for each piece of equipment and its corresponding list of tasks.

The document may contain:
- Multiple equipment sections (e.g., codes like "CH-01", "PUMP-A12", "System 1", etc.)
- Different tasks under each equipment
- Irrelevant data like dates, status, remarks, and signatures

Instructions:
1. Identify all equipment sections and extract:
   - Equipment name (as written)
   - List of tasks (verbatim task descriptions)

2. Ignore:
   - Signatures
   - Reviewer/approver names
   - Date/status/corrected/remarks fields
   - Company/site/document headers

3. Output as JSON using this structure:
{
  "success": true,
  "confidence": 0.95,
  "processing_method": "gpt-4-vision",
  "metadata": {
    "title": "[optional]",
    "document_type": "inspection_checklist"
  },
  "systems": [
    {
      "name": "[Equipment name]",
      "tasks": [
        {"number": 1, "description": "[Task 1]", "type": "inspection"},
        {"number": 2, "description": "[Task 2]", "type": "inspection"}
      ]
    }
  ],
  "total_systems": X,
  "total_tasks": Y
}

Notes:
- Keep task descriptions and equipment names exactly as seen in the PDF.
- Maintain original task order.
- If tasks aren't numbered in the source, assign numbers sequentially.
- Repeat this format for each equipment.
- Don't summarize or guess — extract only what is explicitly present.
"""

def get_ai_prompt_for_document_type(doc_type: str = "general") -> str:
    """Get dynamic prompt that adapts to any document type"""

    base_prompt = AI_EXTRACTION_PROMPT

    # Add dynamic guidance based on detected document characteristics
    dynamic_guidance = """

ADAPTIVE PROCESSING INSTRUCTIONS:
Based on the document content, intelligently adapt your extraction approach:

1. STRUCTURED DOCUMENT RECOGNITION:
   - Look for REPEATING PATTERNS across pages/sections
   - Equipment names are typically in HEADERS or SECTION TITLES
   - Task lists appear UNDER equipment headers in numbered format
   - Same task structure often repeats for different equipment

2. EQUIPMENT IDENTIFICATION:
   - Equipment names are usually BOLD, LARGER, or PROMINENT
   - Look for patterns like "System 1", "System 2", "Equipment A", "Equipment B"
   - Equipment names often include numbers or identifiers
   - Don't confuse document headers (Company, Date) with equipment names

3. TASK EXTRACTION RULES:
   - Tasks are NUMBERED LISTS (1, 2, 3, 4, 5, 6, 7, etc.)
   - Tasks start with ACTION WORDS: "Check", "Inspect", "Verify", "Test"
   - Tasks appear in TABLE FORMAT under equipment headers
   - Extract EXACT wording from the "Tasks" column or list

4. MULTI-PAGE DOCUMENTS:
   - Each page often represents ONE piece of equipment
   - Look for incrementing numbers: "system 1", "system 2", "system 3"
   - Same task list may repeat for each equipment
   - Extract ALL equipment instances, not just the first one

5. COMMON MISTAKES TO AVOID:
   - Don't extract document metadata as equipment names
   - Don't extract table headers as task descriptions
   - Don't combine different equipment into one system
   - Don't skip equipment because tasks are similar

6. QUALITY ASSURANCE:
   - If you find repeating patterns, that's GOOD - extract all instances
   - If task lists are identical across equipment, that's NORMAL
   - Set high confidence for well-structured documents
   - Note any unclear sections in warnings

REMEMBER: Your goal is to be a smart document reader, not a template filler!
"""

    return base_prompt + dynamic_guidance

def validate_ai_response(response_data: Dict[str, Any]) -> tuple[bool, str, Optional[AIExtractionResult]]:
    """
    Validate AI response against schema
    
    Returns:
        (is_valid, error_message, parsed_result)
    """
    try:
        # Parse and validate using Pydantic
        result = AIExtractionResult(**response_data)
        return True, "Valid", result
    
    except Exception as e:
        return False, f"Schema validation error: {str(e)}", None

def create_fallback_result(error_message: str) -> AIExtractionResult:
    """Create a fallback result when AI processing fails"""
    return AIExtractionResult(
        success=False,
        confidence=0.0,
        processing_method="fallback",
        metadata=None,
        processing_time=None,
        systems=[
            SystemSchema(
                name="General Inspection Checklist",
                description="Fallback system created due to processing error",
                category="general",
                location=None,
                manufacturer=None,
                model=None,
                tasks=[
                    TaskSchema(
                        number=1,
                        description="Visual inspection of equipment condition",
                        type=TaskType.inspection,
                        requirements=None,
                        safety_notes=None,
                        estimated_time=None
                    ),
                    TaskSchema(
                        number=2,
                        description="Check for any visible damage or wear",
                        type=TaskType.inspection,
                        requirements=None,
                        safety_notes=None,
                        estimated_time=None
                    ),
                    TaskSchema(
                        number=3,
                        description="Verify proper operation",
                        type=TaskType.inspection,
                        requirements=None,
                        safety_notes=None,
                        estimated_time=None
                    )
                ]
            )
        ],
        total_systems=1,
        total_tasks=3,
        extraction_quality=QualityLevel.poor,
        warnings=[f"AI processing failed: {error_message}"]
    )
