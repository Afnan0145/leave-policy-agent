# Quick Start - 5 Minutes to Running Agent

## Prerequisites Checklist

* [ ] Python 3.12+ installed
* [ ] OpenAI API key
* [ ] Terminal/Command Prompt access

---

## 3-Step Setup

### Step 1: Install Dependencies (2 minutes)

```bash
# Navigate to project directory
cd leave-policy-agent

# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure API Key (1 minute)

```bash
# The .env file is already created, just edit it
nano .env  # or use any text editor

# Replace this line:
OPENAI_API_KEY=sk-your-openai-api-key-here

# With your actual key:
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
```

**That's it! Everything else has default values.**

### Step 3: Run the Agent (30 seconds)

Choose one option:

#### Option A: Interactive CLI (Recommended for testing)

```bash
python -m src.agents.leave_agent
```

Then chat with the agent:

```
You: How many PTO days do US employees get?
Agent: US employees receive 20 PTO days per year...
```

#### Option B: API Server (For REST API testing)

```bash
python -m src.api.main
```

Then test with curl:

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many PTO days do US employees get?"}'
```

---

## Verify Installation

```bash
# Check Python version
python --version  # Should be 3.12+

# Check virtual environment is activated
which python  # Should point to venv/bin/python

# Test imports
python -c "import src.agents.leave_agent; print('✅ All imports successful')"

# Run tests (optional)
pytest tests/ -v
```

---

## Test Scenarios

Try these questions with the agent:

1. **Basic Policy Query**
   ```
   How many PTO days do US employees get?
   ```
2. **Specific Policy Details**
   ```
   What's the carryover limit for US PTO?
   ```
3. **Different Country**
   ```
   What leave types are available in India?
   ```
4. **Eligibility Check**
   ```
   Can I take parental leave? My employee ID is EMP001
   ```
5. **Multi-turn Context**
   ```
   User: What are the leave policies for US?
   Agent: [explains US policies]
   User: What about sick leave?
   Agent: [remembers we're talking about US]
   ```

---

## Common Issues & Fixes

### Issue 1: "Module not found"

```bash
# Solution: Make sure venv is activated
source venv/bin/activate
pip install -r requirements.txt
```

### Issue 2: "OpenAI API key not found"

```bash
# Solution: Check .env file exists and has correct key
cat .env | grep OPENAI_API_KEY
# Should show: OPENAI_API_KEY=sk-proj-xxx...
```

### Issue 3: "Port already in use"

```bash
# Solution: Change port in .env
API_PORT=8081

# Or kill process using port 8080
lsof -i :8080  # Find PID
kill -9 <PID>
```

### Issue 4: "Import errors"

```bash
# Solution: You might be in wrong directory
pwd  # Should end with /leave-policy-agent
cd leave-policy-agent
```

---

## API Endpoints Quick Reference

| Endpoint     | Method | Description        | Example                                |
| ------------ | ------ | ------------------ | -------------------------------------- |
| `/`        | GET    | Service info       | `curl http://localhost:8080/`        |
| `/chat`    | POST   | Chat with agent    | See below                              |
| `/health`  | GET    | Health check       | `curl http://localhost:8080/health`  |
| `/metrics` | GET    | Prometheus metrics | `curl http://localhost:8080/metrics` |
| `/stats`   | GET    | Agent statistics   | `curl http://localhost:8080/stats`   |

### Chat API Example

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many PTO days do US employees get?",
    "session_id": "user-123"
  }'
```

**With Employee Context:**

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can I take parental leave?",
    "session_id": "user-123",
    "user_context": {
      "employee_id": "EMP001",
      "country": "US"
    }
  }'
```

---

## Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term

# Run specific test file
pytest tests/test_tools.py -v

# Run and generate HTML coverage report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

---

## Docker Quick Start (Optional)

```bash
# Build image
docker build -t leave-policy-agent .

# Run container
docker run -p 8080:8080 --env-file .env leave-policy-agent

# Test
curl http://localhost:8080/health
```

---

## Next Steps

1. **Read Full Documentation**
   * `README.md` - Complete documentation
   * `SETUP_GUIDE.md` - Detailed setup with troubleshooting
   * `PROJECT_SUMMARY.md` - Project overview
2. **Explore the Code**
   * `src/agents/leave_agent.py` - Main agent logic
   * `src/tools/` - Custom tools
   * `src/api/main.py` - FastAPI application
3. **Customize**
   * Add more leave policies in `config/leave_policies.py`
   * Modify system instructions in agent
   * Add new tools as needed
4. **Deploy**
   * Follow Cloud Run deployment guide in README.md
   * Set up CI/CD with cloudbuild.yaml

---

## Pro Tips

1. **Use Mock Snowflake** : Keep `USE_MOCK_SNOWFLAKE=true` for development
2. **Check Logs** : Add `LOG_LEVEL=DEBUG` to .env for detailed logs
3. **Interactive Testing** : Use CLI mode for quick testing
4. **API Testing** : Use Postman or curl for API testing
5. **Save Sessions** : Use consistent `session_id` for conversation continuity

---

## Need Help?

1. **Check logs** - Most issues show up in logs
2. **Review SETUP_GUIDE.md** - Detailed troubleshooting
3. **Run tests** - Verify everything works: `pytest tests/ -v`
4. **Contact support** -afnankhan67445@gmail.com

---

## you're Ready!

If you can run the agent and get responses, you're all set!

**Try it now:**

```bash
python -m src.agents.leave_agent
```

Then ask: "How many PTO days do US employees get?"
