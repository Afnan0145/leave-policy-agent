# Step-by-Step Setup Guide

This guide will walk you through setting up and running the Leave Policy Agent from scratch.

## Table of Contents

1. [Prerequisites](https://claude.ai/chat/ffc79467-a04f-4b7f-a364-af1eafdb114d#prerequisites)
2. [Local Setup](https://claude.ai/chat/ffc79467-a04f-4b7f-a364-af1eafdb114d#local-setup)
3. [Running Locally](https://claude.ai/chat/ffc79467-a04f-4b7f-a364-af1eafdb114d#running-locally)
4. [Running Tests](https://claude.ai/chat/ffc79467-a04f-4b7f-a364-af1eafdb114d#running-tests)
5. [Docker Setup](https://claude.ai/chat/ffc79467-a04f-4b7f-a364-af1eafdb114d#docker-setup)
6. [Cloud Deployment](https://claude.ai/chat/ffc79467-a04f-4b7f-a364-af1eafdb114d#cloud-deployment)
7. [Troubleshooting](https://claude.ai/chat/ffc79467-a04f-4b7f-a364-af1eafdb114d#troubleshooting)

---

## Prerequisites

### Required Software

* **Python 3.12+** - [Download](https://www.python.org/downloads/)
* **Git** - [Download](https://git-scm.com/downloads)
* **Google Cloud SDK** (for deployment) - [Install](https://cloud.google.com/sdk/docs/install)
* **Docker** (optional, for containerization) - [Install](https://docs.docker.com/get-docker/)

### Required Accounts

* **OpenAI API Key** - Sign up at [platform.openai.com](https://platform.openai.com/)
* **Google Cloud Project** (for deployment) - [Create](https://console.cloud.google.com/)
* **Snowflake Account** (optional, can use mock mode) - [Sign up](https://signup.snowflake.com/)

---

## Local Setup

### Step 1: Clone or Extract the Repository

```bash
# If you have a git repository
git clone <repository-url>
cd leave-policy-agent

# If you have a ZIP file, extract it and navigate to the directory
cd leave-policy-agent
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Verify activation (should show path to venv)
which python  # macOS/Linux
where python  # Windows
```

### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

### Step 4: Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env file with your values
nano .env  # or use any text editor
```

**Required variables in `.env`:**

```bash
# CRITICAL: Get your OpenAI API key from https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx

# Model to use (gpt-4o-mini is cost-effective)
LLM_MODEL=gpt-4o-mini

# Use mock Snowflake for testing (no Snowflake account needed)
USE_MOCK_SNOWFLAKE=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080

# Logging
LOG_LEVEL=INFO
```

**Optional variables (for real Snowflake):**

```bash
SNOWFLAKE_ACCOUNT=your-account.snowflakecomputing.com
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_DATABASE=LEAVE_DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
```

---

## Running Locally

### Method 1: Interactive CLI (Recommended for Testing)

```bash
# Make sure venv is activated
source venv/bin/activate

# Run the agent in interactive mode
python -m src.agents.leave_agent
```

**Example conversation:**

```
You: How many PTO days do US employees get?
Agent: US employees receive 20 PTO (Paid Time Off) days per year...

You: What about sick leave?
Agent: For US employees, sick leave policy includes...

You: Can I take parental leave? My employee ID is EMP001
Agent: Let me check your eligibility...
```

### Method 2: FastAPI Server (Recommended for API Testing)

```bash
# Make sure venv is activated
source venv/bin/activate

# Start the API server
python -m src.api.main
```

**You should see:**

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### Method 3: Using Uvicorn Directly

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## Testing the API

### Using curl

```bash
# Test health endpoint
curl http://localhost:8080/health

# Test chat endpoint
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many PTO days do US employees get?",
    "session_id": "test-123"
  }'

# Test with employee context
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can I take parental leave?",
    "session_id": "test-123",
    "user_context": {
      "employee_id": "EMP001",
      "country": "US"
    }
  }'

# Get metrics
curl http://localhost:8080/metrics

# Get stats
curl http://localhost:8080/stats

# Reset session
curl -X POST http://localhost:8080/reset/test-123
```

### Using Python requests

```python
import requests

# Chat request
response = requests.post(
    "http://localhost:8080/chat",
    json={
        "message": "How many PTO days do US employees get?",
        "session_id": "user-123"
    }
)

print(response.json())
```

### Using Postman or Insomnia

1. Import the API at `http://localhost:8080`
2. Create a POST request to `/chat`
3. Set headers: `Content-Type: application/json`
4. Body example:

```json
{
  "message": "How many PTO days do US employees get?",
  "session_id": "test-123"
}
```

---

## Running Tests

### Run All Tests

```bash
# Make sure venv is activated
source venv/bin/activate

# Run all tests with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Run Specific Test Files

```bash
# Test agent only
pytest tests/test_agent.py -v

# Test API only
pytest tests/test_api.py -v

# Run with verbose output
pytest tests/ -v -s
```

### Expected Output

```
tests/test_agent.py::TestLeavePolicyTool::test_get_policy_us_pto PASSED
tests/test_agent.py::TestEligibilityTool::test_eligible_employee PASSED
tests/test_api.py::TestChatEndpoint::test_chat_success PASSED
...

---------- coverage: platform linux, python 3.12.0 -----------
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
src/__init__.py                             1      0   100%
src/agents/leave_agent.py                 150     10    93%
src/tools/leave_policy_tool.py             85      5    94%
...
-----------------------------------------------------------
TOTAL                                    1000     80    92%
```

---

## Docker Setup

### Build Docker Image

```bash
# Build image
docker build -t leave-policy-agent .

# Verify image
docker images | grep leave-policy-agent
```

### Run Docker Container

```bash
# Run with environment file
docker run -p 8080:8080 --env-file .env leave-policy-agent

# Run with inline env vars
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=your-key \
  -e USE_MOCK_SNOWFLAKE=true \
  leave-policy-agent

# Run in detached mode
docker run -d -p 8080:8080 --env-file .env --name leave-agent leave-policy-agent

# View logs
docker logs -f leave-agent

# Stop container
docker stop leave-agent

# Remove container
docker rm leave-agent
```

### Docker Compose (Optional)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  agent:
    build: .
    ports:
      - "8080:8080"
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Run with:

```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

---

## Cloud Deployment

### Prerequisites

1. **Install Google Cloud SDK:**

```bash
# Follow: https://cloud.google.com/sdk/docs/install
gcloud version
```

2. **Login and Set Project:**

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud config list
```

3. **Enable Required APIs:**

```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable firestore.googleapis.com
```

### Create Secrets

```bash
# Create OpenAI API key secret
echo -n "sk-your-openai-key" | gcloud secrets create openai-api-key --data-file=-

# Verify
gcloud secrets describe openai-api-key

# Create Snowflake password (if using real Snowflake)
echo -n "your-snowflake-password" | gcloud secrets create snowflake-password --data-file=-
```

### Deploy Using Cloud Build

```bash
# Submit build
gcloud builds submit --config cloudbuild.yaml

# This will:
# 1. Build Docker image
# 2. Push to Container Registry
# 3. Deploy to Cloud Run
```

### Deploy Manually

```bash
# Deploy to Cloud Run
gcloud run deploy leave-policy-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project) \
  --set-env-vars USE_MOCK_SNOWFLAKE=true \
  --set-secrets OPENAI_API_KEY=openai-api-key:latest \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10

# Get the service URL
gcloud run services describe leave-policy-agent --region us-central1 --format 'value(status.url)'
```

### Test Deployed Service

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe leave-policy-agent --region us-central1 --format 'value(status.url)')

# Test health
curl $SERVICE_URL/health

# Test chat
curl -X POST $SERVICE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many PTO days do US employees get?"}'
```

### View Logs

```bash
# Stream logs
gcloud run services logs tail leave-policy-agent --region us-central1

# View in Cloud Console
# https://console.cloud.google.com/run
```

---

## Troubleshooting

### Common Issues

#### 1. Module Not Found Error

**Problem:**

```
ModuleNotFoundError: No module named 'src'
```

**Solution:**

```bash
# Make sure you're in the project root
pwd  # Should end with /leave-policy-agent

# Make sure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### 2. OpenAI API Key Error

**Problem:**

```
Error: OpenAI API key not found
```

**Solution:**

```bash
# Check .env file exists and has the key
cat .env | grep OPENAI_API_KEY

# Make sure the key starts with "sk-"
# Get key from: https://platform.openai.com/api-keys

# Reload environment
source .env  # or restart your terminal
```

#### 3. Port Already in Use

**Problem:**

```
Error: Address already in use
```

**Solution:**

```bash
# Find process using port 8080
lsof -i :8080  # macOS/Linux
netstat -ano | findstr :8080  # Windows

# Kill the process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Or use a different port
export API_PORT=8081
python -m src.api.main
```

#### 4. Tests Failing

**Problem:**

```
Tests fail with import errors or assertion errors
```

**Solution:**

```bash
# Clear pytest cache
pytest --cache-clear

# Reinstall dependencies
pip install -r requirements.txt

# Run tests with verbose output
pytest tests/ -v -s

# Run specific failing test
pytest tests/test_agent.py::TestLeavePolicyTool::test_get_policy_us_pto -v
```

#### 5. Docker Build Fails

**Problem:**

```
Docker build fails with network or dependency errors
```

**Solution:**

```bash
# Clear Docker cache
docker system prune -a

# Build with no cache
docker build --no-cache -t leave-policy-agent .

# Check Docker resources
docker system df
```

#### 6. Cloud Run Deployment Fails

**Problem:**

```
ERROR: (gcloud.run.deploy) Deployment failed
```

**Solution:**

```bash
# Check quota and billing
gcloud beta billing projects describe $(gcloud config get-value project)

# Verify APIs are enabled
gcloud services list --enabled

# Check service account permissions
gcloud projects get-iam-policy $(gcloud config get-value project)

# View detailed error logs
gcloud run deploy leave-policy-agent --verbosity=debug
```

---

## Next Steps

Once everything is running:

1. **Explore the Agent:**
   * Try different questions about leave policies
   * Test eligibility checks with different employee IDs
   * Experiment with multi-turn conversations
2. **Customize:**
   * Add more leave policies in `config/leave_policies.py`
   * Modify system instructions in `src/agents/leave_agent.py`
   * Add more tools if needed
3. **Monitor:**
   * Check `/metrics` endpoint for Prometheus metrics
   * View logs for debugging
   * Monitor circuit breaker states in `/health`
4. **Scale:**
   * Configure auto-scaling in Cloud Run
   * Set up alerting and monitoring
   * Add caching layer for better performance

---

## Support

If you encounter issues:

1. Check the logs: `docker logs <container>` or Cloud Run logs
2. Verify environment variables: `echo $OPENAI_API_KEY`
3. Test individual components: Run tests for specific modules
4. Review the [README.md](https://claude.ai/chat/README.md) for detailed documentation

For assignment-related questions:

* Email: afnankhan67445@gmail.com
* Include: error logs, steps to reproduce, environment details
