"""
Leave Policy Tool - Retrieves leave policy information
"""

import logging
from typing import Optional, Dict, Any

from config.leave_policies import (
    get_leave_policy,
    list_countries,
    list_leave_types,
    LEAVE_POLICIES
)

logger = logging.getLogger(__name__)


class LeavePolicyTool:
    """
    Tool for looking up leave policies by country and type
    
    This tool helps the agent answer questions about:
    - Annual leave allowances
    - Carryover limits
    - Notice period requirements
    - Approval requirements
    - Blackout periods
    """
    
    name = "get_leave_policy"
    description = """
    Get leave policy details for a specific country and leave type.
    
    Use this tool when the user asks about:
    - How many leave days are allowed
    - Leave policy rules and requirements
    - Carryover limits
    - Notice periods
    - Approval requirements
    - Available leave types
    
    Parameters:
    - country (required): Country code (US, India, UK)
    - leave_type (optional): Specific leave type (e.g., "PTO", "Sick Leave", "Parental Leave")
    
    If leave_type is not provided, returns all leave types for that country.
    """
    
    def __init__(self):
        """Initialize the leave policy tool"""
        self.supported_countries = list_countries()
        logger.info(
            f"LeavePolicyTool initialized with countries: {self.supported_countries}"
        )
    
    def __call__(
        self,
        country: str,
        leave_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the tool to get leave policy
        
        Args:
            country: Country code (US, India, UK)
            leave_type: Specific leave type (optional)
            
        Returns:
            Dictionary with policy details or error message
        """
        logger.info(
            f"Looking up leave policy: country={country}, leave_type={leave_type}"
        )
        
        # Normalize country input
        country = country.upper().strip()
        
        # Validate country
        if country not in self.supported_countries:
            error_msg = (
                f"Country '{country}' not supported. "
                f"Supported countries are: {', '.join(self.supported_countries)}"
            )
            logger.warning(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "supported_countries": self.supported_countries
            }
        
        # Get policy
        policy = get_leave_policy(country, leave_type)
        
        if policy is None:
            # Check if it's because leave_type is invalid
            if leave_type:
                available_types = list_leave_types(country)
                error_msg = (
                    f"Leave type '{leave_type}' not found for {country}. "
                    f"Available types: {', '.join(available_types)}"
                )
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "country": country,
                    "available_leave_types": available_types
                }
            else:
                error_msg = f"No leave policies found for {country}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
        
        # Format successful response
        response = {
            "success": True,
            "country": country,
            "policies": policy
        }
        
        if leave_type:
            response["leave_type"] = leave_type
        else:
            response["available_leave_types"] = list(policy.keys())
        
        logger.info(f"Successfully retrieved policy for {country}")
        return response
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for the tool
        Used by ADK for function calling
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "country": {
                        "type": "string",
                        "description": "Country code (US, India, UK)",
                        "enum": self.supported_countries
                    },
                    "leave_type": {
                        "type": "string",
                        "description": (
                            "Optional: Specific leave type to query. "
                            "Examples: 'PTO', 'Sick Leave', 'Parental Leave', "
                            "'Privilege Leave', 'Casual Leave'"
                        )
                    }
                },
                "required": ["country"]
            }
        }


def format_policy_for_display(policy_data: Dict[str, Any]) -> str:
    """
    Format policy data for human-readable display
    
    Args:
        policy_data: Policy data from tool
        
    Returns:
        Formatted string
    """
    if not policy_data.get("success"):
        return f"Error: {policy_data.get('error', 'Unknown error')}"
    
    country = policy_data["country"]
    policies = policy_data["policies"]
    
    output = [f"Leave Policies for {country}:"]
    output.append("=" * 50)
    
    for leave_name, details in policies.items():
        output.append(f"\n{leave_name}:")
        output.append("-" * 30)
        
        for key, value in details.items():
            # Format key nicely
            display_key = key.replace("_", " ").title()
            
            # Format value
            if isinstance(value, bool):
                display_value = "Yes" if value else "No"
            elif isinstance(value, list):
                display_value = ", ".join(str(v) for v in value)
            else:
                display_value = str(value)
            
            output.append(f"  {display_key}: {display_value}")
    
    return "\n".join(output)


# Create singleton instance
leave_policy_tool = LeavePolicyTool()