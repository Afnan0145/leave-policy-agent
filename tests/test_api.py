"""
Test suite for FastAPI endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import json

from src.api.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_agent():
    """Mock agent fixture"""
    with patch('src.api.main.agent') as mock:
        mock.chat.return_value = "Test response from agent"
        mock.reset_conversation.return_value = None
        mock.model = "gpt-4o-mini"
        mock.tools = {
            "get_leave_policy": Mock(),
            "check_leave_eligibility": Mock()
        }
        yield mock


class TestRootEndpoint:
    """Tests for root endpoint"""
    
    def test_root(self, client):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Leave Policy Assistant Agent"
        assert "endpoints" in data


class TestChatEndpoint:
    """Tests for chat endpoint"""
    
    def test_chat_success(self, client, mock_agent):
        """Test successful chat"""
        payload = {
            "message": "How many PTO days do US employees get?",
            "session_id": "test-123"
        }
        
        response = client.post("/chat", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["session_id"] == "test-123"
        assert "timestamp" in data
    
    def test_chat_with_context(self, client, mock_agent):
        """Test chat with user context"""
        payload = {
            "message": "Can I take leave?",
            "session_id": "test-123",
            "user_context": {
                "employee_id": "EMP001",
                "country": "US"
            }
        }
        
        response = client.post("/chat", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
    
    def test_chat_empty_message(self, client):
        """Test chat with empty message"""
        payload = {
            "message": ""
        }
        
        response = client.post("/chat", json=payload)
        
        # Should fail validation
        assert response.status_code == 422
    
    def test_chat_too_long_message(self, client):
        """Test chat with message exceeding max length"""
        payload = {
            "message": "x" * 10001  # Exceeds max_length=10000
        }
        
        response = client.post("/chat", json=payload)
        
        # Should fail validation
        assert response.status_code == 422


class TestResetEndpoint:
    """Tests for reset endpoint"""
    
    def test_reset_session(self, client, mock_agent):
        """Test session reset"""
        response = client.post("/reset/test-session-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "test-session-123" in data["message"]


class TestHealthEndpoint:
    """Tests for health check endpoint"""
    
    @patch('src.api.main.snowflake_client')
    def test_health_check_healthy(self, mock_sf_client, client, mock_agent):
        """Test health check when healthy"""
        mock_sf_client.health_check.return_value = True
        mock_sf_client.get_stats.return_value = {
            "mode": "mock",
            "session_active": False
        }
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "components" in data
        assert "agent" in data["components"]
        assert "snowflake" in data["components"]


class TestMetricsEndpoint:
    """Tests for metrics endpoint"""
    
    def test_metrics(self, client):
        """Test Prometheus metrics endpoint"""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        # Prometheus format includes these markers
        content = response.text
        assert "# HELP" in content or "# TYPE" in content or len(content) > 0


class TestStatsEndpoint:
    """Tests for stats endpoint"""
    
    @patch('src.api.main.snowflake_client')
    def test_stats(self, mock_sf_client, client, mock_agent):
        """Test stats endpoint"""
        mock_sf_client.get_stats.return_value = {
            "mode": "mock",
            "circuit_breaker": {}
        }
        
        response = client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "agent" in data
        assert "circuit_breakers" in data
        assert "timestamp" in data


class TestErrorHandling:
    """Tests for error handling"""
    
    def test_404_not_found(self, client):
        """Test 404 handling"""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
    
    @patch('src.api.main.agent', None)
    def test_chat_agent_not_initialized(self, client):
        """Test chat when agent is not initialized"""
        payload = {
            "message": "Test message"
        }
        
        response = client.post("/chat", json=payload)
        
        assert response.status_code == 503
        data = response.json()
        assert "Agent not initialized" in data["error"]


class TestMiddleware:
    """Tests for middleware"""
    
    def test_process_time_header(self, client):
        """Test that process time header is added"""
        response = client.get("/")
        
        assert "X-Process-Time" in response.headers
        # Should be a valid float
        float(response.headers["X-Process-Time"])


class TestCORS:
    """Tests for CORS middleware"""
    
    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options(
            "/chat",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # CORS middleware should add these headers
        assert "access-control-allow-origin" in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])