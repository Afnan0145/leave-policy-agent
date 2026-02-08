"""
Test suite for Leave Policy Agent
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.agents.leave_agent import LeaveAgent
from src.tools.leave_policy_tool import leave_policy_tool
from src.tools.eligibility_tool import eligibility_tool
from config.leave_policies import LEAVE_POLICIES, MOCK_EMPLOYEES


class TestLeavePolicyTool:
    """Tests for leave policy tool"""
    
    def test_get_policy_us_pto(self):
        """Test getting US PTO policy"""
        result = leave_policy_tool(country="US", leave_type="PTO")
        
        assert result["success"] is True
        assert result["country"] == "US"
        assert "PTO" in result["policies"]
        assert result["policies"]["PTO"]["annual_allowance"] == 20
    
    def test_get_policy_india_all(self):
        """Test getting all India policies"""
        result = leave_policy_tool(country="India")
        
        assert result["success"] is True
        assert result["country"] == "INDIA"
        assert "Privilege Leave" in result["policies"]
        assert "Casual Leave" in result["policies"]
    
    def test_invalid_country(self):
        """Test invalid country"""
        result = leave_policy_tool(country="invalid")
        
        assert result["success"] is False
        assert "not supported" in result["error"]
    
    def test_invalid_leave_type(self):
        """Test invalid leave type"""
        result = leave_policy_tool(country="US", leave_type="InvalidLeave")
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    def test_case_insensitive(self):
        """Test case insensitive country"""
        result1 = leave_policy_tool(country="us", leave_type="pto")
        result2 = leave_policy_tool(country="US", leave_type="PTO")
        
        assert result1["success"] is True
        assert result2["success"] is True


class TestEligibilityTool:
    """Tests for eligibility tool"""
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_eligible_employee(self, mock_snowflake):
        """Test eligible employee"""
        # Mock Snowflake client
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        # Create new eligibility tool instance with mocked client
        from src.tools.eligibility_tool import EligibilityTool
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="EMP001",
            leave_type="PTO",
            days_requested=5
        )
        
        assert result["success"] is True
        assert result["eligible"] is True
        assert result["employee_id"] == "EMP001"
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_insufficient_balance(self, mock_snowflake):
        """Test insufficient leave balance"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = MOCK_EMPLOYEES["EMP001"]
        mock_snowflake.return_value = mock_client
        
        from src.tools.eligibility_tool import EligibilityTool
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="EMP001",
            leave_type="PTO",
            days_requested=50  # More than balance
        )
        
        assert result["success"] is True
        assert result["eligible"] is False
        assert any("Insufficient" in r for r in result.get("reasons", []))
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_employee_not_found(self, mock_snowflake):
        """Test employee not found"""
        mock_client = Mock()
        mock_client.get_employee_by_id.return_value = None
        mock_snowflake.return_value = mock_client
        
        from src.tools.eligibility_tool import EligibilityTool
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="INVALID",
            leave_type="PTO"
        )
        
        assert result["success"] is False
        assert result["eligible"] is False
        assert "not found" in result["error"]
    
    @patch('src.tools.eligibility_tool.get_snowflake_client')
    def test_tenure_requirement(self, mock_snowflake):
        """Test tenure requirement check"""
        mock_client = Mock()
        
        # Employee with insufficient tenure
        employee = MOCK_EMPLOYEES["EMP003"].copy()
        employee["tenure_months"] = 2  # Less than required 12 months
        
        mock_client.get_employee_by_id.return_value = employee
        mock_snowflake.return_value = mock_client
        
        from src.tools.eligibility_tool import EligibilityTool
        tool = EligibilityTool()
        tool.snowflake_client = mock_client
        
        result = tool(
            employee_id="EMP003",
            leave_type="Parental Leave"
        )
        
        assert result["success"] is True
        # Check if tenure check exists and failed
        tenure_checks = [c for c in result["checks"] if "Tenure" in c["check_name"]]
        if tenure_checks:
            assert not tenure_checks[0]["passed"]


class TestCallbacks:
    """Tests for before/after model callbacks"""
    
    def test_before_model_pii_detection(self):
        """Test PII detection in before_model callback"""
        from src.callbacks.before_model import before_model_callback
        
        messages = [
            {
                "role": "user",
                "content": "My SSN is 123-45-6789"
            }
        ]
        
        result = before_model_callback(messages)
        
        assert result["metadata"]["pii_detected"]["ssn"] is True
        assert result["metadata"]["pii_masked"] is True
    
    def test_before_model_sql_injection(self):
        """Test SQL injection detection"""
        from src.callbacks.before_model import before_model_callback
        
        messages = [
            {
                "role": "user",
                "content": "SELECT * FROM users WHERE id=1; DROP TABLE employees"
            }
        ]
        
        result = before_model_callback(messages)
        
        assert result["metadata"]["validation_passed"] is False
        assert any("injection" in issue.lower() for issue in result["metadata"]["issues"])
    
    def test_after_model_pii_removal(self):
        """Test PII removal in after_model callback"""
        from src.callbacks.after_model import after_model_callback
        
        response = "Your SSN is 123-45-6789 and credit card is 4532-1234-5678-9010"
        
        result = after_model_callback(response)
        
        assert "123-45-6789" not in result["response"]
        assert "4532-1234-5678-9010" not in result["response"]
        assert result["metadata"]["pii_removed"] is True


class TestLeaveAgent:
    """Tests for the main Leave Agent"""
    
    @patch('src.agents.leave_agent.completion')
    def test_agent_initialization(self, mock_completion):
        """Test agent initialization"""
        agent = LeaveAgent()
        
        assert agent is not None
        assert len(agent.tools) == 2
        assert "get_leave_policy" in agent.tools
        assert "check_leave_eligibility" in agent.tools
    
    @patch('src.agents.leave_agent.completion')
    def test_simple_conversation(self, mock_completion):
        """Test simple conversation"""
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(
                content="US employees get 20 PTO days per year.",
                tool_calls=None
            ))
        ]
        mock_completion.return_value = mock_response
        
        agent = LeaveAgent()
        response = agent.chat("How many PTO days do US employees get?")
        
        assert response is not None
        assert len(response) > 0
    
    @patch('src.agents.leave_agent.completion')
    def test_conversation_history(self, mock_completion):
        """Test conversation history tracking"""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="Test response", tool_calls=None))
        ]
        mock_completion.return_value = mock_response
        
        agent = LeaveAgent()
        
        agent.chat("First message")
        agent.chat("Second message")
        
        history = agent.get_conversation_history()
        
        assert len(history) == 4  # 2 user + 2 assistant messages
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
    
    @patch('src.agents.leave_agent.completion')
    def test_reset_conversation(self, mock_completion):
        """Test conversation reset"""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="Test", tool_calls=None))
        ]
        mock_completion.return_value = mock_response
        
        agent = LeaveAgent()
        
        agent.chat("Message")
        assert len(agent.get_conversation_history()) > 0
        
        agent.reset_conversation()
        assert len(agent.get_conversation_history()) == 0


class TestCircuitBreaker:
    """Tests for circuit breaker"""
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state"""
        from src.integrations.circuit_breaker import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=3, timeout=10)
        
        # Should allow calls
        def test_func():
            return "success"
        
        result = cb.call(test_func)
        assert result == "success"
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold"""
        from src.integrations.circuit_breaker import CircuitBreaker, CircuitBreakerError
        
        cb = CircuitBreaker(failure_threshold=3, timeout=10)
        
        def failing_func():
            raise Exception("Service down")
        
        # Fail threshold times
        for _ in range(3):
            try:
                cb.call(failing_func)
            except Exception:
                pass
        
        # Circuit should be open now
        with pytest.raises(CircuitBreakerError):
            cb.call(failing_func)


class TestSnowflakeClient:
    """Tests for Snowflake client"""
    
    def test_mock_mode(self):
        """Test Snowflake client in mock mode"""
        from src.integrations.snowflake_client import SnowflakeClient
        
        client = SnowflakeClient(use_mock=True)
        
        employee = client.get_employee_by_id("EMP001")
        
        assert employee is not None
        assert employee["employee_id"] == "EMP001"
        assert employee["country"] == "US"
    
    def test_employee_not_found(self):
        """Test employee not found in mock mode"""
        from src.integrations.snowflake_client import SnowflakeClient
        
        client = SnowflakeClient(use_mock=True)
        
        employee = client.get_employee_by_id("INVALID")
        
        assert employee is None
    
    def test_query_by_country(self):
        """Test querying employees by country"""
        from src.integrations.snowflake_client import SnowflakeClient
        
        client = SnowflakeClient(use_mock=True)
        
        us_employees = client.query_employees_by_country("US")
        
        assert len(us_employees) > 0
        assert all(emp["country"] == "US" for emp in us_employees)


# Pytest configuration
@pytest.fixture
def agent():
    """Fixture for agent instance"""
    with patch('src.agents.leave_agent.completion'):
        return LeaveAgent()


@pytest.fixture
def mock_llm_response():
    """Fixture for mocked LLM response"""
    mock_response = Mock()
    mock_response.choices = [
        Mock(message=Mock(content="Test response", tool_calls=None))
    ]
    return mock_response


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src", "--cov-report=html"])