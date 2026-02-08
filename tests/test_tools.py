"""
Test suite for Agent Tools
Comprehensive tests for leave policy and eligibility tools
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.tools.leave_policy_tool import (
    LeavePolicyTool,
    leave_policy_tool,
    format_policy_for_display
)
from src.tools.eligibility_tool import (
    EligibilityTool,
    eligibility_tool
)
from config.leave_policies import (
    LEAVE_POLICIES,
    MOCK_EMPLOYEES,
    get_leave_policy,
    get_employee_data,
    list_countries,
    list_leave_types
)


class TestLeavePolicyTool:
    """Tests for Leave Policy Tool"""
    
    def test_tool_initialization(self):
        """Test tool is properly initialized"""
        tool = LeavePolicyTool()
        
        assert tool.name == "get_leave_policy"
        assert tool.description is not None
        assert len(tool.supported_countries) > 0
        assert "US" in tool.supported_countries
        assert "India" in tool.supported_countries
    
    def test_get_us_pto_policy(self):
        """Test getting US PTO policy"""
        result = leave_policy_tool(country="US", leave_type="PTO")
        
        assert result["success"] is True
        assert result["country"] == "US"
        assert result["leave_type"] == "PTO"
        assert "PTO" in result["policies"]
        
        pto_policy = result["policies"]["PTO"]
        assert pto_policy["annual_allowance"] == 20
        assert pto_policy["carryover_limit"] == 5
        assert pto_policy["min_notice_days"] == 3
        assert pto_policy["max_consecutive_days"] == 10
    
    def test_get_us_sick_leave_policy(self):
        """Test getting US Sick Leave policy"""
        result = leave_policy_tool(country="US", leave_type="Sick Leave")
        
        assert result["success"] is True
        assert "Sick Leave" in result["policies"]
        
        sick_policy = result["policies"]["Sick Leave"]
        assert sick_policy["annual_allowance"] == 10
        assert sick_policy["carryover_limit"] == 0
        assert sick_policy["min_notice_days"] == 0
    
    def test_get_us_parental_leave_policy(self):
        """Test getting US Parental Leave policy"""
        result = leave_policy_tool(country="US", leave_type="Parental Leave")
        
        assert result["success"] is True
        assert "Parental Leave" in result["policies"]
        
        parental_policy = result["policies"]["Parental Leave"]
        assert parental_policy["allowance_weeks"] == 16
        assert parental_policy["eligibility_months"] == 12
        assert parental_policy["paid"] is True
    
    def test_get_all_us_policies(self):
        """Test getting all US policies without specifying type"""
        result = leave_policy_tool(country="US")
        
        assert result["success"] is True
        assert result["country"] == "US"
        assert "available_leave_types" in result
        assert len(result["policies"]) >= 3
        assert "PTO" in result["policies"]
        assert "Sick Leave" in result["policies"]
        assert "Parental Leave" in result["policies"]
    
    def test_get_india_privilege_leave(self):
        """Test getting India Privilege Leave policy"""
        result = leave_policy_tool(country="India", leave_type="Privilege Leave")
        
        assert result["success"] is True
        assert result["country"] == "INDIA"
        assert "Privilege Leave" in result["policies"]
        
        pl_policy = result["policies"]["Privilege Leave"]
        assert pl_policy["annual_allowance"] == 18
        assert pl_policy["carryover_limit"] == 30
        assert pl_policy["min_notice_days"] == 7
        assert pl_policy["encashment_allowed"] is True
    
    def test_get_india_casual_leave(self):
        """Test getting India Casual Leave policy"""
        result = leave_policy_tool(country="India", leave_type="Casual Leave")
        
        assert result["success"] is True
        assert "Casual Leave" in result["policies"]
        
        cl_policy = result["policies"]["Casual Leave"]
        assert cl_policy["annual_allowance"] == 12
        assert cl_policy["max_consecutive_days"] == 3
    
    def test_get_all_india_policies(self):
        """Test getting all India policies"""
        result = leave_policy_tool(country="India")
        
        assert result["success"] is True
        assert "Privilege Leave" in result["policies"]
        assert "Casual Leave" in result["policies"]
        assert "Sick Leave" in result["policies"]
        assert "Optional Holidays" in result["policies"]
    
    def test_get_uk_policies(self):
        """Test getting UK policies"""
        result = leave_policy_tool(country="UK")
        
        assert result["success"] is True
        assert result["country"] == "UK"
        assert "Annual Leave" in result["policies"]
        assert "Sick Leave" in result["policies"]
    
    def test_case_insensitive_country(self):
        """Test that country lookup is case-insensitive"""
        result1 = leave_policy_tool(country="us")
        result2 = leave_policy_tool(country="US")
        result3 = leave_policy_tool(country="Us")
        
        assert result1["success"] is True
        assert result2["success"] is True
        assert result3["success"] is True
        assert result1["country"] == "US"
        assert result2["country"] == "US"
        assert result3["country"] == "US"
    
    def test_case_insensitive_leave_type(self):
        """Test that leave type lookup is case-insensitive"""
        result1 = leave_policy_tool(country="US", leave_type="pto")
        result2 = leave_policy_tool(country="US", leave_type="PTO")
        result3 = leave_policy_tool(country="US", leave_type="Pto")
        
        assert result1["success"] is True
        assert result2["success"] is True
        assert result3["success"] is True
    
    def test_invalid_country(self):
        """Test handling of invalid country"""
        result = leave_policy_tool(country="InvalidCountry")
        
        assert result["success"] is False
        assert "not supported" in result["error"]
        assert "supported_countries" in result
        assert len(result["supported_countries"]) > 0
    
    def test_invalid_leave_type(self):
        """Test handling of invalid leave type"""
        result = leave_policy_tool(country="US", leave_type="InvalidLeave")
        
        assert result["success"] is False
        assert "not found" in result["error"]
        assert "available_leave_types" in result
        assert result["country"] == "US"
    
    def test_whitespace_handling(self):
        """Test handling of whitespace in inputs"""
        result = leave_policy_tool(country="  US  ", leave_type="  PTO  ")
        
        assert result["success"] is True
        assert result["country"] == "US"
    
    def test_tool_schema(self):
        """Test that tool schema is properly defined"""
        tool = LeavePolicyTool()
        schema = tool.get_schema()
        
        assert schema["name"] == "get_leave_policy"
        assert "description" in schema
        assert "parameters" in schema
        assert "properties" in schema["parameters"]
        assert "country" in schema["parameters"]["properties"]
        assert "leave_type" in schema["parameters"]["properties"]
        assert "required" in schema["parameters"]
        assert "country" in schema["parameters"]["required"]
    
    def test_format_policy_for_display(self):
        """Test policy formatting for display"""
        policy_data = {
            "success": True,
            "country": "US",
            "policies": {
                "PTO": {
                    "annual_allowance": 20,
                    "carryover_limit": 5
                }
            }
        }
        
        formatted = format_policy_for_display(policy_data)
        
        assert "US" in formatted
        assert "PTO" in formatted
        assert "20" in formatted
    
    def test_format_policy_error(self):
        """Test formatting error messages"""
        policy_data = {
            "success": False,
            "error": "Country not found"
        }
        
        formatted = format_policy_for_display(policy_data)
        
        assert "Error" in formatted
        assert "Country not found" in formatted


class TestEligibilityTool:
    """Tests for Eligibility Tool"""
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_tool_initialization(self, mock_snowflake):
        """Test tool is properly initialized"""
        mock_client = Mock()
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        
        assert tool.name == "check_leave_eligibility"
        assert tool.description is not None
        assert tool.snowflake_client is not None
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_eligible_employee_basic(self, mock_snowflake):
        """Test basic eligibility check for eligible employee"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="EMP001",
            leave_type="PTO"
        )
        
        assert result["success"] is True
        assert result["eligible"] is True
        assert result["employee_id"] == "EMP001"
        assert result["employee_name"] == "John Doe"
        assert result["country"] == "US"
        assert result["leave_type"] == "PTO"
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_eligible_with_days_requested(self, mock_snowflake):
        """Test eligibility with specific days requested"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="EMP001",
            leave_type="PTO",
            days_requested=5
        )
        
        assert result["success"] is True
        assert result["eligible"] is True
        
        # Check that balance check was performed
        balance_checks = [c for c in result["checks"] if "Balance" in c["check_name"]]
        assert len(balance_checks) > 0
        assert balance_checks[0]["passed"] is True
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_insufficient_balance(self, mock_snowflake):
        """Test employee with insufficient leave balance"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="EMP001",
            leave_type="PTO",
            days_requested=50  # More than available (15)
        )
        
        assert result["success"] is True
        assert result["eligible"] is False
        assert "reasons" in result
        assert any("Insufficient" in r for r in result["reasons"])
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_employee_not_found(self, mock_snowflake):
        """Test handling when employee is not found"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = None
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="INVALID123",
            leave_type="PTO"
        )
        
        assert result["success"] is False
        assert result["eligible"] is False
        assert "not found" in result["error"].lower()
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_invalid_leave_type(self, mock_snowflake):
        """Test handling when leave type is not found"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="EMP001",
            leave_type="InvalidLeave"
        )
        
        assert result["success"] is False
        assert result["eligible"] is False
        assert "not found" in result["error"].lower()
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_tenure_requirement_met(self, mock_snowflake):
        """Test eligibility with tenure requirement met"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="EMP001",
            leave_type="Parental Leave"  # Requires 12 months tenure
        )
        
        assert result["success"] is True
        
        # EMP001 has 14 months tenure, should pass
        tenure_checks = [c for c in result["checks"] if "Tenure" in c["check_name"]]
        if tenure_checks:
            assert tenure_checks[0]["passed"] is True
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_tenure_requirement_not_met(self, mock_snowflake):
        """Test eligibility with insufficient tenure"""
        mock_client = Mock()
        
        # Create employee with insufficient tenure
        employee = MOCK_EMPLOYEES["EMP003"].copy()
        employee["tenure_months"] = 2  # Less than required
        employee["country"] = "US"  # Change to US for Parental Leave
        
        mock_client.get_employee_by_id.return_value = employee
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="EMP003",
            leave_type="Parental Leave"  # Requires 12 months
        )
        
        assert result["success"] is True
        assert result["eligible"] is False
        
        tenure_checks = [c for c in result["checks"] if "Tenure" in c["check_name"]]
        if tenure_checks:
            assert tenure_checks[0]["passed"] is False
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_notice_period_sufficient(self, mock_snowflake):
        """Test eligibility with sufficient notice period"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        # Request leave 10 days from now (more than 3 days required)
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        
        result = tool(
            employee_id="EMP001",
            leave_type="PTO",
            start_date=future_date
        )
        
        assert result["success"] is True
        
        notice_checks = [c for c in result["checks"] if "Notice" in c["check_name"]]
        if notice_checks:
            assert notice_checks[0]["passed"] is True
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_notice_period_insufficient(self, mock_snowflake):
        """Test eligibility with insufficient notice period"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        # Request leave tomorrow (less than 3 days required for PTO)
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        result = tool(
            employee_id="EMP001",
            leave_type="PTO",
            start_date=tomorrow
        )
        
        assert result["success"] is True
        assert result["eligible"] is False
        
        notice_checks = [c for c in result["checks"] if "Notice" in c["check_name"]]
        if notice_checks:
            assert notice_checks[0]["passed"] is False
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_consecutive_days_within_limit(self, mock_snowflake):
        """Test eligibility with days within consecutive limit"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="EMP001",
            leave_type="PTO",
            days_requested=7  # Within 10-day limit
        )
        
        assert result["success"] is True
        
        consecutive_checks = [c for c in result["checks"] if "Consecutive" in c["check_name"]]
        if consecutive_checks:
            assert consecutive_checks[0]["passed"] is True
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_consecutive_days_exceeds_limit(self, mock_snowflake):
        """Test eligibility with days exceeding consecutive limit"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="EMP001",
            leave_type="PTO",
            days_requested=15  # Exceeds 10-day limit
        )
        
        assert result["success"] is True
        assert result["eligible"] is False
        
        consecutive_checks = [c for c in result["checks"] if "Consecutive" in c["check_name"]]
        if consecutive_checks:
            assert consecutive_checks[0]["passed"] is False
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_blackout_period_check(self, mock_snowflake):
        """Test eligibility during blackout period"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        # December 25 falls in blackout period (Dec 20-31)
        result = tool(
            employee_id="EMP001",
            leave_type="PTO",
            start_date="2025-12-25"
        )
        
        assert result["success"] is True
        
        blackout_checks = [c for c in result["checks"] if "Blackout" in c["check_name"]]
        if blackout_checks:
            assert blackout_checks[0]["passed"] is False
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_invalid_date_format(self, mock_snowflake):
        """Test handling of invalid date format"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="EMP001",
            leave_type="PTO",
            start_date="invalid-date"
        )
        
        assert result["success"] is True
        # Should have a failed check for invalid date
        notice_checks = [c for c in result["checks"] if "Notice" in c["check_name"]]
        if notice_checks:
            assert notice_checks[0]["passed"] is False
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_tool_schema(self, mock_snowflake):
        """Test that tool schema is properly defined"""
        mock_client = Mock()
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        schema = tool.get_schema()
        
        assert schema["name"] == "check_leave_eligibility"
        assert "description" in schema
        assert "parameters" in schema
        assert "employee_id" in schema["parameters"]["properties"]
        assert "leave_type" in schema["parameters"]["properties"]
        assert "start_date" in schema["parameters"]["properties"]
        assert "days_requested" in schema["parameters"]["properties"]
        assert "employee_id" in schema["parameters"]["required"]
        assert "leave_type" in schema["parameters"]["required"]
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_india_employee_eligibility(self, mock_snowflake):
        """Test eligibility for India employee"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP002"]
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="EMP002",
            leave_type="Privilege Leave",
            days_requested=10
        )
        
        assert result["success"] is True
        assert result["country"] == "India"
        assert result["leave_type"] == "Privilege Leave"
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_complete_eligibility_check(self, mock_snowflake):
        """Test complete eligibility check with all parameters"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        
        result = tool(
            employee_id="EMP001",
            leave_type="PTO",
            start_date=future_date,
            days_requested=5
        )
        
        assert result["success"] is True
        assert "checks" in result
        assert "summary" in result
        assert result["summary"]["total_checks"] > 0


class TestConfigFunctions:
    """Test configuration helper functions"""
    
    def test_get_leave_policy_function(self):
        """Test get_leave_policy helper function"""
        policy = get_leave_policy("US", "PTO")
        
        assert policy is not None
        assert "PTO" in policy
        assert policy["PTO"]["annual_allowance"] == 20
    
    def test_get_employee_data_function(self):
        """Test get_employee_data helper function"""
        employee = get_employee_data("EMP001")
        
        assert employee is not None
        assert employee["employee_id"] == "EMP001"
        assert employee["name"] == "John Doe"
        assert employee["country"] == "US"
    
    def test_list_countries_function(self):
        """Test list_countries helper function"""
        countries = list_countries()
        
        assert len(countries) > 0
        assert "US" in countries
        assert "India" in countries
        assert "UK" in countries
    
    def test_list_leave_types_function(self):
        """Test list_leave_types helper function"""
        us_types = list_leave_types("US")
        
        assert len(us_types) > 0
        assert "PTO" in us_types
        assert "Sick Leave" in us_types
        assert "Parental Leave" in us_types
    
    def test_list_leave_types_invalid_country(self):
        """Test list_leave_types with invalid country"""
        types = list_leave_types("InvalidCountry")
        
        assert types == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.tools", "--cov-report=term"])