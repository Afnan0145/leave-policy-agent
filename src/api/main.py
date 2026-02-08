"""
FastAPI Application for Leave Policy Agent
Provides REST API endpoints for the agent
"""

import os
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Import agent and integrations
from src.agents.leave_agent import LeaveAgent
from src.integrations.circuit_breaker import get_all_circuit_breaker_stats
from src.integrations.snowflake_client import get_snowflake_client

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'leave_agent_requests_total',
    'Total requests to the leave agent',
    ['endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'leave_agent_request_duration_seconds',
    'Request duration in seconds',
    ['endpoint']
)

CHAT_MESSAGES = Counter(
    'leave_agent_chat_messages_total',
    'Total chat messages processed'
)

# Global agent instance
agent: Optional[LeaveAgent] = None
snowflake_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown
    """
    # Startup
    global agent, snowflake_client
    
    logger.info("Starting Leave Policy Agent API...")
    
    # Initialize agent
    agent = LeaveAgent()
    logger.info("Agent initialized")
    
    # Initialize Snowflake client
    snowflake_client = get_snowflake_client()
    logger.info("Snowflake client initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Leave Policy Agent API...")
    
    if snowflake_client:
        snowflake_client.close()
        logger.info("Snowflake client closed")


# Create FastAPI app
app = FastAPI(
    title="Leave Policy Assistant Agent",
    description="AI agent for leave policy questions and eligibility checks",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., description="User message", min_length=1, max_length=10000)
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    user_context: Optional[Dict[str, Any]] = Field(None, description="User context (employee_id, country, etc.)")
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "message": "How many PTO days do US employees get?",
                "session_id": "user-123",
                "user_context": {
                    "employee_id": "EMP001",
                    "country": "US"
                }
            }]
        }
    }


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str = Field(..., description="Agent response")
    session_id: Optional[str] = Field(None, description="Session ID")
    timestamp: str = Field(..., description="Response timestamp")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    components: Dict[str, Any]


# Middleware for request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add timing and logging middleware"""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    process_time = time.time() - start_time
    
    # Add header
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log request
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {process_time:.3f}s"
    )
    
    # Record metrics
    REQUEST_DURATION.labels(endpoint=request.url.path).observe(process_time)
    REQUEST_COUNT.labels(
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    return response


# API Endpoints
@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint"""
    return {
        "service": "Leave Policy Assistant Agent",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/chat",
            "health": "/health",
            "metrics": "/metrics"
        }
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the leave policy agent
    
    Args:
        request: Chat request with message and optional context
        
    Returns:
        Agent response
        
    Raises:
        HTTPException: If agent is not initialized or processing fails
    """
    if agent is None:
        raise HTTPException(
            status_code=503,
            detail="Agent not initialized"
        )
    
    try:
        # Record metric
        CHAT_MESSAGES.inc()
        
        # Process message
        response = agent.chat(
            message=request.message,
            session_id=request.session_id,
            user_context=request.user_context
        )
        
        return ChatResponse(
            response=response,
            session_id=request.session_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )


@app.post("/reset/{session_id}")
async def reset_session(session_id: str):
    """
    Reset a conversation session
    
    Args:
        session_id: Session ID to reset
        
    Returns:
        Success message
    """
    if agent is None:
        raise HTTPException(
            status_code=503,
            detail="Agent not initialized"
        )
    
    try:
        agent.reset_conversation(session_id)
        
        return {
            "status": "success",
            "message": f"Session {session_id} reset",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        
    except Exception as e:
        logger.error(f"Error resetting session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting session: {str(e)}"
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Checks:
    - Agent status
    - Snowflake connection
    - Circuit breaker states
    
    Returns:
        Health status
    """
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Check agent
    agent_healthy = agent is not None
    
    # Check Snowflake
    snowflake_healthy = False
    snowflake_stats = {}
    
    if snowflake_client:
        snowflake_healthy = snowflake_client.health_check()
        snowflake_stats = snowflake_client.get_stats()
    
    # Check circuit breakers
    circuit_breakers = get_all_circuit_breaker_stats()
    
    # Determine overall status
    overall_healthy = agent_healthy and (snowflake_healthy or snowflake_stats.get("mode") == "mock")
    
    status = "healthy" if overall_healthy else "degraded"
    
    return HealthResponse(
        status=status,
        timestamp=timestamp,
        components={
            "agent": {
                "status": "healthy" if agent_healthy else "unhealthy",
                "initialized": agent_healthy
            },
            "snowflake": {
                "status": "healthy" if snowflake_healthy else "unhealthy",
                **snowflake_stats
            },
            "circuit_breakers": circuit_breakers
        }
    )


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint
    
    Returns:
        Prometheus-formatted metrics
    """
    return generate_latest().decode('utf-8')


@app.get("/stats")
async def get_stats():
    """
    Get agent statistics
    
    Returns:
        Statistics about the agent
    """
    if agent is None:
        raise HTTPException(
            status_code=503,
            detail="Agent not initialized"
        )
    
    stats = {
        "agent": {
            "model": agent.model,
            "tools_count": len(agent.tools),
            "tools": list(agent.tools.keys())
        },
        "circuit_breakers": get_all_circuit_breaker_stats(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    if snowflake_client:
        stats["snowflake"] = snowflake_client.get_stats()
    
    return stats


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else "An unexpected error occurred",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    )


# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8080))
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )