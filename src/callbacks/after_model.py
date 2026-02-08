"""
After Model Callback - Content filtering and post-processing
Executed after the LLM generates a response
"""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class AfterModelCallback:
    """
    Callback executed after LLM inference
    
    Responsibilities:
    - Content filtering
    - Response validation
    - Format enforcement
    - PII leakage prevention
    - Response enhancement
    """
    
    def __init__(self):
        """Initialize after model callback"""
        # Prohibited content patterns
        self.prohibited_patterns = {
            "profanity": re.compile(
                r'\b(damn|hell|crap)\b',  # Mild examples for demo
                re.IGNORECASE
            ),
            "discriminatory": re.compile(
                r'\b(discriminat|bias|prejudice)\b',
                re.IGNORECASE
            )
        }
        
        # PII patterns (shouldn't appear in responses)
        self.pii_patterns = {
            "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            "credit_card": re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
        }
        
        logger.info("AfterModelCallback initialized")
    
    def __call__(
        self,
        response: str,
        messages: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process LLM response before returning to user
        
        Args:
            response: LLM generated response
            messages: Conversation history
            **kwargs: Additional context
            
        Returns:
            Dictionary with processed response and metadata
        """
        logger.debug("AfterModelCallback processing response")
        
        # Run validation checks
        validation_results = self._validate_response(response)
        
        # Filter prohibited content
        filtered_response = self._filter_content(response)
        
        # Check for PII leakage
        pii_check = self._check_pii_leakage(filtered_response)
        
        if pii_check["pii_found"]:
            logger.warning(f"PII detected in response: {pii_check['types']}")
            filtered_response = self._remove_pii(filtered_response)
        
        # Enhance response formatting
        enhanced_response = self._enhance_formatting(filtered_response)
        
        # Add helpful context if needed
        final_response = self._add_context(
            enhanced_response,
            validation_results,
            pii_check
        )
        
        return {
            "response": final_response,
            "metadata": {
                "filtered": filtered_response != response,
                "pii_removed": pii_check["pii_found"],
                "validation_passed": validation_results["passed"],
                "issues": validation_results.get("issues", []),
                "original_length": len(response),
                "final_length": len(final_response)
            }
        }
    
    def _validate_response(self, response: str) -> Dict[str, Any]:
        """
        Validate LLM response
        
        Args:
            response: Generated text
            
        Returns:
            Validation results
        """
        issues = []
        
        # Check length
        if len(response) < 10:
            issues.append("Response too short")
        
        if len(response) > 5000:
            issues.append("Response too long")
        
        # Check for incomplete sentences
        if response and not response.rstrip().endswith(('.', '!', '?', '"', "'")):
            issues.append("Response appears incomplete")
        
        # Check for hallucination markers
        hallucination_markers = [
            "I don't have access to",
            "I cannot verify",
            "I'm not sure",
            "I don't know"
        ]
        
        has_uncertainty = any(
            marker.lower() in response.lower()
            for marker in hallucination_markers
        )
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "length": len(response),
            "has_uncertainty": has_uncertainty
        }
    
    def _filter_content(self, response: str) -> str:
        """
        Filter prohibited content from response
        
        Args:
            response: Original response
            
        Returns:
            Filtered response
        """
        filtered = response
        
        # Check for prohibited patterns
        for content_type, pattern in self.prohibited_patterns.items():
            if pattern.search(filtered):
                logger.warning(f"Prohibited content detected: {content_type}")
                # Replace with asterisks
                filtered = pattern.sub("***", filtered)
        
        return filtered
    
    def _check_pii_leakage(self, response: str) -> Dict[str, Any]:
        """
        Check if response contains PII
        
        Args:
            response: Text to check
            
        Returns:
            PII detection results
        """
        pii_types = []
        
        for pii_type, pattern in self.pii_patterns.items():
            if pattern.search(response):
                pii_types.append(pii_type)
        
        return {
            "pii_found": len(pii_types) > 0,
            "types": pii_types
        }
    
    def _remove_pii(self, response: str) -> str:
        """
        Remove PII from response
        
        Args:
            response: Text with potential PII
            
        Returns:
            Text with PII removed
        """
        cleaned = response
        
        # Remove SSN
        cleaned = self.pii_patterns["ssn"].sub("[SSN REMOVED]", cleaned)
        
        # Remove credit card
        cleaned = self.pii_patterns["credit_card"].sub(
            "[CREDIT CARD REMOVED]",
            cleaned
        )
        
        return cleaned
    
    def _enhance_formatting(self, response: str) -> str:
        """
        Enhance response formatting for better readability
        
        Args:
            response: Original response
            
        Returns:
            Enhanced response
        """
        enhanced = response
        
        # Ensure proper spacing after punctuation
        enhanced = re.sub(r'([.!?])([A-Z])', r'\1 \2', enhanced)
        
        # Remove excessive whitespace
        enhanced = re.sub(r'\s+', ' ', enhanced)
        
        # Remove leading/trailing whitespace
        enhanced = enhanced.strip()
        
        # Ensure consistent list formatting
        enhanced = re.sub(r'\n-\s*', '\n- ', enhanced)
        enhanced = re.sub(r'\n\d+\.\s*', lambda m: m.group(0), enhanced)
        
        return enhanced
    
    def _add_context(
        self,
        response: str,
        validation_results: Dict[str, Any],
        pii_check: Dict[str, Any]
    ) -> str:
        """
        Add helpful context or disclaimers to response
        
        Args:
            response: Enhanced response
            validation_results: Validation results
            pii_check: PII check results
            
        Returns:
            Response with context
        """
        final = response
        
        # Add disclaimer if PII was removed
        if pii_check["pii_found"]:
            disclaimer = (
                "\n\n*Note: Some sensitive information was removed "
                "from this response for security.*"
            )
            final += disclaimer
        
        # Add help text if response has uncertainty
        if validation_results.get("has_uncertainty"):
            help_text = (
                "\n\nIf you need more specific information, please provide "
                "your employee ID and the specific leave type you're asking about."
            )
            # Only add if not already present
            if "employee ID" not in final:
                final += help_text
        
        return final
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get callback statistics"""
        return {
            "callback_name": "after_model",
            "prohibited_patterns_count": len(self.prohibited_patterns),
            "pii_patterns_count": len(self.pii_patterns)
        }


# Create singleton instance
after_model_callback = AfterModelCallback()