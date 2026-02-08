"""
Leave Eligibility Tool - Checks if employee is eligible for leave
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from config.leave_policies import get_leave_policy
from src.integrations.snowflake_client import get_snowflake_client

logger = logging.getLogger(__name__)


class EligibilityTool:
    """
    Tool for checking leave eligibility
    
    Checks:
    - Tenure requirements
    - Leave balance availability
    - Notice period requirements
    - Blackout periods
    - Maximum consecutive days
    """
    
    name = "check_leave_eligibility"
    description = """
    Check if an employee is eligible to take a specific type of leave.
    
    Use this tool when the user asks:
    - "Can I take leave?"
    - "Am I eligible for parental leave?"
    - "Do I have enough PTO?"
    - Questions about eligibility or availability
    
    Parameters:
    - employee_id (required): Employee identifier (e.g., "EMP001")
    - leave_type (required): Type of leave (e.g., "PTO", "Sick Leave")
    - start_date (optional): Requested start date (YYYY-MM-DD)
    - days_requested (optional): Number of days requested
    
    Returns eligibility status with detailed reasons.
    """
    
    def __init__(self):
        """Initialize eligibility tool"""
        self.snowflake_client = get_snowflake_client()
        logger.info("EligibilityTool initialized")
    
    def __call__(
        self,
        employee_id: str,
        leave_type: str,
        start_date: Optional[str] = None,
        days_requested: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Check leave eligibility
        
        Args:
            employee_id: Employee ID
            leave_type: Leave type to check
            start_date: Optional start date (YYYY-MM-DD)
            days_requested: Optional number of days
            
        Returns:
            Eligibility result with details
        """
        logger.info(
            f"Checking eligibility: employee={employee_id}, "
            f"leave_type={leave_type}, start_date={start_date}, "
            f"days={days_requested}"
        )
        
        # Get employee data
        employee = self.snowflake_client.get_employee_by_id(employee_id)
        
        if not employee:
            return {
                "success": False,
                "eligible": False,
                "error": f"Employee {employee_id} not found",
                "employee_id": employee_id
            }
        
        country = employee["country"]
        
        # Get leave policy
        policy = get_leave_policy(country, leave_type)
        
        if not policy:
            return {
                "success": False,
                "eligible": False,
                "error": f"Leave type '{leave_type}' not found for country {country}",
                "employee_id": employee_id,
                "country": country
            }
        
        # Get the specific policy details
        policy_details = list(policy.values())[0]
        
        # Perform eligibility checks
        checks = self._perform_eligibility_checks(
            employee,
            leave_type,
            policy_details,
            start_date,
            days_requested
        )
        
        # Determine overall eligibility
        eligible = all(check["passed"] for check in checks["checks"])
        
        response = {
            "success": True,
            "eligible": eligible,
            "employee_id": employee_id,
            "employee_name": employee["name"],
            "country": country,
            "leave_type": leave_type,
            "checks": checks["checks"],
            "summary": checks["summary"]
        }
        
        if not eligible:
            response["reasons"] = [
                check["reason"] for check in checks["checks"]
                if not check["passed"]
            ]
        
        logger.info(
            f"Eligibility check complete: eligible={eligible} for {employee_id}"
        )
        
        return response
    
    def _perform_eligibility_checks(
        self,
        employee: Dict[str, Any],
        leave_type: str,
        policy: Dict[str, Any],
        start_date: Optional[str],
        days_requested: Optional[int]
    ) -> Dict[str, Any]:
        """
        Perform all eligibility checks
        
        Returns:
            Dictionary with check results
        """
        checks = []
        
        # 1. Tenure check (for leaves that require minimum tenure)
        if "eligibility_months" in policy:
            tenure_check = self._check_tenure(
                employee["tenure_months"],
                policy["eligibility_months"],
                leave_type
            )
            checks.append(tenure_check)
        
        # 2. Leave balance check
        if days_requested and "annual_allowance" in policy:
            balance_check = self._check_balance(
                employee["leave_balance"].get(leave_type, 0),
                days_requested,
                leave_type
            )
            checks.append(balance_check)
        
        # 3. Notice period check
        if start_date and "min_notice_days" in policy:
            notice_check = self._check_notice_period(
                start_date,
                policy["min_notice_days"],
                leave_type
            )
            checks.append(notice_check)
        
        # 4. Consecutive days check
        if days_requested and "max_consecutive_days" in policy:
            consecutive_check = self._check_consecutive_days(
                days_requested,
                policy["max_consecutive_days"],
                leave_type
            )
            checks.append(consecutive_check)
        
        # 5. Blackout period check
        if start_date and "blackout_periods" in policy:
            blackout_check = self._check_blackout_period(
                start_date,
                policy["blackout_periods"],
                leave_type
            )
            checks.append(blackout_check)
        
        # Generate summary
        passed_count = sum(1 for check in checks if check["passed"])
        total_count = len(checks)
        
        summary = {
            "total_checks": total_count,
            "passed_checks": passed_count,
            "failed_checks": total_count - passed_count
        }
        
        return {
            "checks": checks,
            "summary": summary
        }
    
    def _check_tenure(
        self,
        tenure_months: int,
        required_months: int,
        leave_type: str
    ) -> Dict[str, Any]:
        """Check if employee has sufficient tenure"""
        passed = tenure_months >= required_months
        
        return {
            "check_name": "Tenure Requirement",
            "passed": passed,
            "reason": (
                f"Employee has {tenure_months} months of tenure "
                f"(required: {required_months} months for {leave_type})"
                if passed else
                f"Insufficient tenure: {tenure_months} months "
                f"(need {required_months} months for {leave_type})"
            ),
            "details": {
                "current_tenure_months": tenure_months,
                "required_tenure_months": required_months
            }
        }
    
    def _check_balance(
        self,
        current_balance: int,
        days_requested: int,
        leave_type: str
    ) -> Dict[str, Any]:
        """Check if employee has sufficient leave balance"""
        passed = current_balance >= days_requested
        
        return {
            "check_name": "Leave Balance",
            "passed": passed,
            "reason": (
                f"Sufficient {leave_type} balance: {current_balance} days available "
                f"(requesting {days_requested} days)"
                if passed else
                f"Insufficient {leave_type} balance: only {current_balance} days available "
                f"(requesting {days_requested} days)"
            ),
            "details": {
                "current_balance": current_balance,
                "days_requested": days_requested,
                "remaining_after": current_balance - days_requested if passed else None
            }
        }
    
    def _check_notice_period(
        self,
        start_date: str,
        min_notice_days: int,
        leave_type: str
    ) -> Dict[str, Any]:
        """Check if notice period requirement is met"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            today = datetime.now()
            days_notice = (start - today).days
            
            passed = days_notice >= min_notice_days
            
            return {
                "check_name": "Notice Period",
                "passed": passed,
                "reason": (
                    f"Notice period met: {days_notice} days notice "
                    f"(required: {min_notice_days} days for {leave_type})"
                    if passed else
                    f"Insufficient notice: {days_notice} days "
                    f"(need {min_notice_days} days for {leave_type})"
                ),
                "details": {
                    "days_notice_given": days_notice,
                    "required_notice_days": min_notice_days,
                    "start_date": start_date
                }
            }
        except ValueError as e:
            return {
                "check_name": "Notice Period",
                "passed": False,
                "reason": f"Invalid start date format: {start_date}. Use YYYY-MM-DD",
                "details": {"error": str(e)}
            }
    
    def _check_consecutive_days(
        self,
        days_requested: int,
        max_consecutive: int,
        leave_type: str
    ) -> Dict[str, Any]:
        """Check if request exceeds maximum consecutive days"""
        passed = days_requested <= max_consecutive
        
        return {
            "check_name": "Consecutive Days Limit",
            "passed": passed,
            "reason": (
                f"Within consecutive days limit: {days_requested} days "
                f"(max: {max_consecutive} days for {leave_type})"
                if passed else
                f"Exceeds consecutive days limit: {days_requested} days "
                f"(max: {max_consecutive} days for {leave_type})"
            ),
            "details": {
                "days_requested": days_requested,
                "max_consecutive_days": max_consecutive
            }
        }
    
    def _check_blackout_period(
        self,
        start_date: str,
        blackout_periods: list,
        leave_type: str
    ) -> Dict[str, Any]:
        """Check if request falls in blackout period"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            
            # Simple check - just check if month/day falls in blackout
            # In production, you'd parse the blackout periods properly
            for period in blackout_periods:
                if "Dec" in period and start.month == 12:
                    return {
                        "check_name": "Blackout Period",
                        "passed": False,
                        "reason": (
                            f"Leave request falls in blackout period: {period}. "
                            f"{leave_type} cannot be taken during this time."
                        ),
                        "details": {
                            "start_date": start_date,
                            "blackout_period": period
                        }
                    }
            
            return {
                "check_name": "Blackout Period",
                "passed": True,
                "reason": f"Leave request does not fall in any blackout period",
                "details": {
                    "start_date": start_date,
                    "blackout_periods": blackout_periods
                }
            }
            
        except ValueError as e:
            return {
                "check_name": "Blackout Period",
                "passed": False,
                "reason": f"Invalid start date format: {start_date}",
                "details": {"error": str(e)}
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for the tool"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "Employee ID (e.g., 'EMP001')"
                    },
                    "leave_type": {
                        "type": "string",
                        "description": (
                            "Type of leave to check eligibility for "
                            "(e.g., 'PTO', 'Sick Leave', 'Parental Leave')"
                        )
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Requested start date in YYYY-MM-DD format"
                    },
                    "days_requested": {
                        "type": "integer",
                        "description": "Number of days requested"
                    }
                },
                "required": ["employee_id", "leave_type"]
            }
        }


# Create singleton instance
eligibility_tool = EligibilityTool()