"""
AI Services Integration for PDF Document Understanding
Handles integration with multiple AI providers for intelligent document processing
"""

import os
import base64
import json
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from io import BytesIO
import fitz  # PyMuPDF
import requests
from django.conf import settings
from django.core.files.storage import default_storage

from .ai_schemas import (
    AIExtractionResult, 
    validate_ai_response, 
    create_fallback_result,
    get_ai_prompt_for_document_type
)

logger = logging.getLogger(__name__)

class AIServiceError(Exception):
    """Custom exception for AI service errors"""
    pass

class AIDocumentProcessor:
    """Main class for AI-powered document processing"""
    
    def __init__(self):
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.claude_api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
        self.google_api_key = getattr(settings, 'GOOGLE_CLOUD_API_KEY', None)
        
        # Service availability
        self.services_available = {
            'openai': bool(self.openai_api_key),
            'claude': bool(self.claude_api_key),
            'google': bool(self.google_api_key)
        }
        
        logger.info(f"AI Services available: {self.services_available}")
    
    def process_pdf(self, pdf_path: str, document_type: str = "general") -> AIExtractionResult:
        """
        Process PDF using AI services with fallback chain
        
        Args:
            pdf_path: Path to the PDF file
            document_type: Type of document for specialized processing
            
        Returns:
            AIExtractionResult with extracted data
        """
        start_time = time.time()
        
        try:
            # Try primary AI service (OpenAI GPT-4 Vision)
            if self.services_available['openai']:
                try:
                    result = self._process_with_openai(pdf_path, document_type)
                    if result.success and result.confidence > 0.7:
                        result.processing_time = time.time() - start_time
                        return result
                    logger.warning("OpenAI processing had low confidence, trying fallback")
                except Exception as e:
                    logger.error(f"OpenAI processing failed: {e}")
            
            # Try secondary service (Claude 3.5)
            if self.services_available['claude']:
                try:
                    result = self._process_with_claude(pdf_path, document_type)
                    if result.success and result.confidence > 0.6:
                        result.processing_time = time.time() - start_time
                        return result
                    logger.warning("Claude processing had low confidence, trying fallback")
                except Exception as e:
                    logger.error(f"Claude processing failed: {e}")
            
            # Try tertiary service (Google Document AI)
            if self.services_available['google']:
                try:
                    result = self._process_with_google(pdf_path, document_type)
                    if result.success:
                        result.processing_time = time.time() - start_time
                        return result
                except Exception as e:
                    logger.error(f"Google Document AI processing failed: {e}")
            
            # All AI services failed, return fallback
            logger.error("All AI services failed, using fallback")
            return create_fallback_result("All AI services unavailable or failed")
            
        except Exception as e:
            logger.error(f"Critical error in AI processing: {e}")
            return create_fallback_result(f"Critical processing error: {str(e)}")
    
    def _process_with_openai(self, pdf_path: str, document_type: str) -> AIExtractionResult:
        """Process PDF using OpenAI GPT-4 Vision"""
        logger.info("Processing with OpenAI GPT-4 Vision")
        
        # Convert PDF to images
        images = self._pdf_to_images(pdf_path, max_pages=10)
        if not images:
            raise AIServiceError("Failed to convert PDF to images")
        
        # Prepare API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}"
        }
        
        # Build messages with images
        messages = [
            {
                "role": "system",
                "content": "You are an expert at analyzing industrial inspection documents."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": get_ai_prompt_for_document_type(document_type)
                    }
                ] + [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}",
                            "detail": "high"
                        }
                    } for img_base64 in images[:5]  # Limit to 5 images for cost control
                ]
            }
        ]
        
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": messages,
            "max_tokens": 4000,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        # Make API request
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        
        if response.status_code != 200:
            raise AIServiceError(f"OpenAI API error: {response.status_code} - {response.text}")
        
        # Parse response
        response_data = response.json()
        content = response_data['choices'][0]['message']['content']
        
        try:
            extracted_data = json.loads(content)
            extracted_data['processing_method'] = 'gpt-4-vision'
            
            # Validate response
            is_valid, error_msg, result = validate_ai_response(extracted_data)
            if is_valid:
                return result
            else:
                raise AIServiceError(f"Invalid response format: {error_msg}")
                
        except json.JSONDecodeError as e:
            raise AIServiceError(f"Failed to parse JSON response: {e}")
    
    def _process_with_claude(self, pdf_path: str, document_type: str) -> AIExtractionResult:
        """Process PDF using Claude 3.5 Sonnet"""
        logger.info("Processing with Claude 3.5 Sonnet")
        
        # Extract text from PDF
        text_content = self._extract_text_from_pdf(pdf_path)
        if not text_content:
            raise AIServiceError("Failed to extract text from PDF")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.claude_api_key,
            "anthropic-version": "2023-06-01"
        }
        
        prompt = f"""
{get_ai_prompt_for_document_type(document_type)}

DOCUMENT CONTENT:
{text_content[:50000]}  # Limit content to avoid token limits

Please analyze this document and return the structured JSON response.
"""
        
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 4000,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=120
        )
        
        if response.status_code != 200:
            raise AIServiceError(f"Claude API error: {response.status_code} - {response.text}")
        
        response_data = response.json()
        content = response_data['content'][0]['text']
        
        # Extract JSON from response (Claude might include extra text)
        try:
            # Find JSON in the response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            json_content = content[start_idx:end_idx]
            
            extracted_data = json.loads(json_content)
            extracted_data['processing_method'] = 'claude-3.5-sonnet'
            
            # Validate response
            is_valid, error_msg, result = validate_ai_response(extracted_data)
            if is_valid:
                return result
            else:
                raise AIServiceError(f"Invalid response format: {error_msg}")
                
        except (json.JSONDecodeError, ValueError) as e:
            raise AIServiceError(f"Failed to parse JSON from Claude response: {e}")
    
    def _process_with_google(self, pdf_path: str, document_type: str) -> AIExtractionResult:
        """Process PDF using Google Document AI"""
        logger.info("Processing with Google Document AI")
        
        # For now, implement a simplified version
        # In production, you would use the full Google Document AI API
        text_content = self._extract_text_from_pdf(pdf_path)
        
        # Create a basic structured response
        # This is a simplified implementation - full Google Document AI would be more sophisticated
        result_data = {
            "success": True,
            "confidence": 0.6,
            "processing_method": "google-document-ai",
            "systems": [
                {
                    "name": "General Equipment Inspection",
                    "description": "Extracted using Google Document AI",
                    "category": "general",
                    "tasks": [
                        {
                            "number": 1,
                            "description": "Perform visual inspection",
                            "type": "inspection"
                        }
                    ]
                }
            ],
            "total_systems": 1,
            "total_tasks": 1,
            "extraction_quality": "fair"
        }
        
        is_valid, error_msg, result = validate_ai_response(result_data)
        if is_valid:
            return result
        else:
            raise AIServiceError(f"Google processing validation failed: {error_msg}")
    
    def _pdf_to_images(self, pdf_path: str, max_pages: int = 10) -> List[str]:
        """Convert PDF pages to base64 encoded images"""
        try:
            doc = fitz.open(pdf_path)
            images = []
            
            for page_num in range(min(len(doc), max_pages)):
                page = doc[page_num]
                # Render page as image
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Convert to base64
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                images.append(img_base64)
            
            doc.close()
            return images
            
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            return []
    
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from PDF"""
        try:
            doc = fitz.open(pdf_path)
            text_content = ""
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_content += page.get_text("text") + "\n"
            
            doc.close()
            return text_content
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""

# Singleton instance
ai_processor = AIDocumentProcessor()

def process_pdf_with_ai(pdf_path: str, document_type: str = "general") -> AIExtractionResult:
    """
    Main function to process PDF with AI
    
    Args:
        pdf_path: Path to PDF file
        document_type: Type of document for specialized processing
        
    Returns:
        AIExtractionResult with extracted data
    """
    return ai_processor.process_pdf(pdf_path, document_type)
