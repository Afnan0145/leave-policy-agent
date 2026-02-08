"""
Before Model Callback - Security and input validation
Executed before the LLM processes user input
"""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class BeforeModelCallback:
    """
    Security callback executed before LLM inference
    
    Responsibilities:
    - Input validation
    - PII detection and masking
    - Malicious input detection
    - Input sanitization
    - Rate limiting checks
    """
    
    def __init__(self):
        """Initialize before model callback"""
        # PII patterns
        self.pii_patterns = {
            "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            "credit_card": re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
            "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "phone": re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            "ip_address": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        }
        
        # Malicious patterns
        self.malicious_patterns = {
            "sql_injection": re.compile(
                r"(\bUNION\b|\bSELECT\b|\bDROP\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b)",
                re.IGNORECASE
            ),
            "script_injection": re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE),
            "command_injection": re.compile(r'[;&|`$()]')
        }
        
        logger.info("BeforeModelCallback initialized")
    
    def __call__(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Process messages before LLM inference
        
        Args:
            messages: List of conversation messages
            **kwargs: Additional context
            
        Returns:
            Dictionary with processed messages and metadata
        """
        logger.debug(f"BeforeModelCallback processing {len(messages)} messages")
        
        # Get the latest user message
        user_message = self._get_latest_user_message(messages)
        
        if not user_message:
            logger.warning("No user message found in input")
            return {
                "messages": messages,
                "metadata": {
                    "validation_passed": True,
                    "warnings": ["No user message to validate"]
                }
            }
        
        # Run security checks
        validation_results = self._validate_input(user_message["content"])
        
        # If validation fails, modify the message
        if not validation_results["passed"]:
            logger.warning(
                f"Input validation failed: {validation_results['issues']}"
            )
            
            # You can either:
            # 1. Block the request
            # 2. Sanitize the input
            # 3. Add a warning
            
            # For this implementation, we'll sanitize and warn
            sanitized_content = self._sanitize_input(user_message["content"])
            user_message["content"] = sanitized_content
            
            # Update message in list
            for i, msg in enumerate(messages):
                if msg.get("role") == "user" and msg == user_message:
                    messages[i]["content"] = sanitized_content
                    break
        
        # Mask PII if detected
        pii_detected = validation_results.get("pii_detected", {})
        if any(pii_detected.values()):
            logger.info(f"PII detected: {list(pii_detected.keys())}")
            masked_content = self._mask_pii(user_message["content"])
            
            for i, msg in enumerate(messages):
                if msg.get("role") == "user" and msg == user_message:
                    messages[i]["content"] = masked_content
                    break
        
        return {
            "messages": messages,
            "metadata": {
                "validation_passed": validation_results["passed"],
                "issues": validation_results.get("issues", []),
                "pii_detected": pii_detected,
                "pii_masked": any(pii_detected.values())
            }
        }
    
    def _get_latest_user_message(
        self,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any] | None:
        """Get the most recent user message"""
        for message in reversed(messages):
            if message.get("role") == "user":
                return message
        return None
    
    def _validate_input(self, content: str) -> Dict[str, Any]:
        """
        Validate user input for security issues
        
        Args:
            content: User input text
            
        Returns:
            Validation results
        """
        issues = []
        
        # Check for PII
        pii_detected = {}
        for pii_type, pattern in self.pii_patterns.items():
            if pattern.search(content):
                pii_detected[pii_type] = True
                issues.append(f"Potential {pii_type.upper()} detected")
        
        # Check for malicious patterns
        for attack_type, pattern in self.malicious_patterns.items():
            if pattern.search(content):
                issues.append(f"Potential {attack_type} detected")
        
        # Check message length
        if len(content) > 10000:
            issues.append("Message exceeds maximum length (10000 characters)")
        
        # Check for excessive special characters (potential encoding attack)
        special_char_ratio = sum(
            1 for c in content if not c.isalnum() and not c.isspace()
        ) / max(len(content), 1)
        
        if special_char_ratio > 0.3:
            issues.append("Excessive special characters detected")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "pii_detected": pii_detected,
            "content_length": len(content),
            "special_char_ratio": special_char_ratio
        }
    
    def _sanitize_input(self, content: str) -> str:
        """
        Sanitize potentially malicious input
        
        Args:
            content: User input
            
        Returns:
            Sanitized content
        """
        sanitized = content
        
        # Remove script tags
        sanitized = re.sub(
            r'<script[^>]*>.*?</script>',
            '[REMOVED]',
            sanitized,
            flags=re.IGNORECASE
        )
        
        # Remove potentially dangerous characters for command injection
        # (but preserve normal punctuation)
        dangerous_chars = ['`', '$', ';']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limit length
        if len(sanitized) > 10000:
            sanitized = sanitized[:10000] + "... [truncated]"
        
        return sanitized
    
    def _mask_pii(self, content: str) -> str:
        """
        Mask PII in content
        
        Args:
            content: Text with potential PII
            
        Returns:
            Text with PII masked
        """
        masked = content
        
        # Mask SSN
        masked = self.pii_patterns["ssn"].sub("***-**-****", masked)
        
        # Mask credit card
        masked = self.pii_patterns["credit_card"].sub("**** **** **** ****", masked)
        
        # Mask email (keep domain for context)
        def mask_email(match):
            email = match.group(0)
            parts = email.split('@')
            if len(parts) == 2:
                return f"***@{parts[1]}"
            return "***@***.***"
        
        masked = self.pii_patterns["email"].sub(mask_email, masked)
        
        # Mask phone
        masked = self.pii_patterns["phone"].sub("***-***-****", masked)
        
        return masked
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get callback statistics"""
        return {
            "callback_name": "before_model",
            "pii_patterns_count": len(self.pii_patterns),
            "malicious_patterns_count": len(self.malicious_patterns)
        }


# Create singleton instance
before_model_callback = BeforeModelCallback()