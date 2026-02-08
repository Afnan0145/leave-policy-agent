# Leave Policy Assistant Agent --pathan afnan khan

A production-grade AI agent built with Google ADK that helps employees with leave policy questions and eligibility checks.

## Architecture

```
┌─────────────┐
│   FastAPI   │ ← REST API Layer
└──────┬──────┘
       │
┌──────▼──────┐
│  ADK Agent  │ ← Core Agent (Multi-turn conversations)
└──────┬──────┘
       │
       ├─────────┬─────────┬──────────┐
       │         │         │          │
   ┌───▼───┐ ┌──▼──┐  ┌───▼────┐ ┌──▼────┐
   │LiteLLM│ │Tools│  │Callbacks│ │Snowflake│
   └───────┘ └─────┘  └────────┘ └────────┘
                                      │
                               Circuit Breaker
```

## Features

* Multi-turn conversation support
* Leave policy lookup by country/type
* Leave eligibility checking
* Snowflake integration with circuit breaker
* Security callbacks (before/after model)
* FastAPI REST API
* Cloud Run deployment ready
* OpenTelemetry observability
* Firestore session persistence
* Structured JSON logging
* Prometheus metrics
* Unit tests (>80% coverage)

## Prerequisites

* Python 3.12+
* Google Cloud Project with:
  * Cloud Run enabled
  * Secret Manager enabled
  * Cloud Build enabled
  * Firestore enabled
* Snowflake account (or mock mode for testing)
* OpenAI API key (or compatible LLM)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd leave-policy-agent
```

### 2. Create Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables

Create a `.env` file:

```bash
# LLM Configuration
OPENAI_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o-mini

# Snowflake Configuration (optional - can use mock mode)
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_USER=your-user
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_DATABASE=LEAVE_DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
USE_MOCK_SNOWFLAKE=true  # Set to false for real Snowflake

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
FIRESTORE_COLLECTION=agent_sessions

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080

# Observability
ENABLE_TRACING=true
LOG_LEVEL=INFO

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60
```

## Running Locally

### Start the API Server

```bash
python -m src.api.main
```

The API will be available at `http://localhost:8080`

### Test with Sample Request

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many PTO days do US employees get?",
    "session_id": "test-session-123"
  }'
```

### Interactive Mode

```bash
python -m src.agents.leave_agent
```

## Running Tests

```bash
# Run all tests with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_agent.py -v

# Run with verbose output
pytest -v -s
```

Coverage report will be in `htmlcov/index.html`

## Docker Build

```bash
# Build image
docker build -t leave-policy-agent .

# Run container
docker run -p 8080:8080 --env-file .env leave-policy-agent
```

## Deployment to Cloud Run

### 1. Set up Google Cloud

```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Login and set project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Create Secrets in Secret Manager

```bash
# OpenAI API Key
echo -n "sk-your-key" | gcloud secrets create openai-api-key --data-file=-

# Snowflake credentials (if using real Snowflake)
echo -n "your-password" | gcloud secrets create snowflake-password --data-file=-
```

### 3. Deploy with Cloud Build

```bash
gcloud builds submit --config cloudbuild.yaml
```

### 4. Deploy Manually

```bash
gcloud run deploy leave-policy-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID \
  --set-secrets OPENAI_API_KEY=openai-api-key:latest
```

## Monitoring

### Metrics Endpoint

```bash
curl http://localhost:8080/metrics
```

### Health Check

```bash
curl http://localhost:8080/health
```

### View Traces

Traces are sent to Google Cloud Trace when deployed:

```
https://console.cloud.google.com/traces
```

## API Endpoints

### POST /chat

Chat with the agent

**Request:**

```json
{
  "message": "How many sick days do I have?",
  "session_id": "user-123",
  "user_context": {
    "employee_id": "EMP001",
    "country": "US"
  }
}
```

**Response:**

```json
{
  "response": "Based on the US leave policy...",
  "session_id": "user-123",
  "timestamp": "2025-02-08T10:30:00Z"
}
```

### GET /health

Health check endpoint

### GET /metrics

Prometheus metrics

## Project Structure

```
leave-policy-agent/
├── src/
│   ├── agents/
│   │   └── leave_agent.py          # Main ADK agent
│   ├── tools/
│   │   ├── leave_policy_tool.py    # Leave policy lookup
│   │   └── eligibility_tool.py     # Eligibility checker
│   ├── callbacks/
│   │   ├── before_model.py         # Pre-processing
│   │   └── after_model.py          # Post-processing
│   ├── integrations/
│   │   ├── snowflake_client.py     # Snowflake connection
│   │   └── circuit_breaker.py      # Resilience pattern
│   └── api/
│       └── main.py                 # FastAPI application
├── tests/
│   ├── test_agent.py
│   ├── test_tools.py
│   └── test_api.py
├── config/
│   └── leave_policies.py           # Mock policy data
├── Dockerfile
├── cloudbuild.yaml
├── requirements.txt
└── README.md
```

## Key Components

### 1. Agent

* Uses Google ADK `Agent` class
* LiteLLM for model integration
* Multi-turn conversation support
* Context preservation via Firestore

### 2. Tools

* **get_leave_policy** : Retrieves policy details
* **check_leave_eligibility** : Validates eligibility

### 3. Callbacks

* **Before Model** : Input validation, PII detection
* **After Model** : Content filtering, response formatting

### 4. Integrations

* **Snowflake** : Employee data access
* **Circuit Breaker** : Prevents cascading failures

## Test Scenarios

The agent handles:

1. **Policy Lookup** : "How many PTO days do US employees get?"
2. **Eligibility Check** : "Can I take parental leave?"
3. **Multi-turn** : "What about sick leave?" (context aware)
4. **Edge Cases** : Invalid dates, unknown leave types
5. **Missing Info** : Prompts for required details

## Security Features

* Input validation in before_model callback
* PII detection and masking
* Content filtering in after_model callback
* Secrets stored in Google Secret Manager
* No hardcoded credentials

## Circuit Breaker

Protects Snowflake integration:

* Fails fast after threshold failures
* Automatic recovery after timeout
* Prevents resource exhaustion

## Performance

* Response time: <2s (typical)
* Concurrent requests: 100+
* Session persistence: Firestore
* Caching: In-memory policy data

## Contributing

This is an evaluation assignment. For questions, contact: afnankhan67445@gmail.com

## License

Confidential - For evaluation purposes only

## Troubleshooting

### Issue: Agent not responding

* Check `OPENAI_API_KEY` is set
* Verify LLM model is available
* Check logs: `docker logs <container-id>`

### Issue: Snowflake connection fails

* Set `USE_MOCK_SNOWFLAKE=true` for testing
* Verify Snowflake credentials
* Check network connectivity

### Issue: Tests failing

* Ensure virtual environment is activated
* Install dev dependencies: `pip install -r requirements.txt`
* Clear pytest cache: `pytest --cache-clear`

## Support

For technical issues during evaluation:

* Email: afnankhan67445@gmail.com
* Include: error logs, steps to reproduce

---

Built with ❤️ using Google ADK
