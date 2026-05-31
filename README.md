# GenAdvisorIQ - AI Financial Advisor

A FastAPI-based financial advisor API powered by Claude AI with MongoDB integration for comprehensive customer context, token tracking, and cost monitoring.

## Features

- **AI-Powered Financial Advice**: Personalized recommendations using Claude AI
- **MongoDB Integration**: Real customer data - agents, customers, assets, liabilities, insurance, goals, etc.
- **Customer Context**: Pulls complete financial profile from MongoDB for richer advice
- **Token Tracking**: Monitor input/output tokens per API call
- **Cost Calculation**: Real-time cost tracking with detailed breakdowns
- **Usage Analytics**: Track total and daily usage statistics
- **RESTful API**: Clean, well-documented endpoints

## Technology Stack

- **Backend**: FastAPI + Uvicorn
- **AI**: Claude API (Anthropic)
- **Database**: MongoDB with Motor (async driver)
- **Data Validation**: Pydantic
- **Environment**: python-dotenv

## Setup

### 1. Install Dependencies
```bash
pip install fastapi uvicorn anthropic pymongo motor python-dotenv pydantic
```

### 2. Environment Configuration
Add your credentials to `.env`:
```bash
# Claude API
CLAUDE_API_KEY=your_claude_api_key_here
CLAUDE_MODEL=claude-3-sonnet-20240229
CLAUDE_MAX_TOKENS=2000
CLAUDE_TEMPERATURE=0.7

# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=genaibot
```

### 3. MongoDB Database Setup
Ensure your MongoDB instance is running and contains the following collections:
- `genaibot.customers` - Customer profiles
- `genaibot.agents` - Bank advisors
- `genaibot.Assets` - Customer assets
- `genaibot.liabilities` - Customer liabilities
- `genaibot.insurance` - Insurance policies
- `genaibot.goal` - Financial goals
- `genaibot.transactions` - Transaction history
- `genaibot.callLogs` - Customer call logs
- `genaibot.dependents` - Customer dependents
- `genaibot.globalVariables` - Global financial parameters

### 4. Run the Application
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### POST `/api/analyze` - Get Financial Advice
Get personalized financial advice based on customer profile and question.

**Request Body**:
```json
{
  "customer_id": "507f1f77bcf86cd799439011",
  "question": "What should be my investment strategy for retirement?"
}
```

**Response**:
```json
{
  "answer": "Based on your financial profile with monthly income of $75,000 and current net worth of $500,000, here are my recommendations...",
  "status": "generated",
  "customer_id": "507f1f77bcf86cd799439011",
  "context_summary": {
    "total_assets": 750000,
    "total_liabilities": 250000,
    "net_worth": 500000
  },
  "metrics": {
    "model": "claude-3-sonnet-20240229",
    "input_tokens": 1245,
    "output_tokens": 580,
    "total_tokens": 1825,
    "cost": {
      "input_cost": 0.003735,
      "output_cost": 0.0087,
      "total_cost": 0.012435,
      "input_rate_per_million": 3.0,
      "output_rate_per_million": 15.0
    }
  }
}
```

### GET `/api/customer/{customer_id}` - Get Customer Profile
Fetch complete financial profile for a customer including all relationships.

**Example**:
```bash
GET /api/customer/507f1f77bcf86cd799439011
```

**Response**:
```json
{
  "customer": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "monthly_income": 75000,
    "monthly_expenses": 50000
  },
  "agent": {
    "username": "agent_john",
    "first_name": "Jane",
    "company": "BankCorp"
  },
  "financial_summary": {
    "total_assets": 750000,
    "total_liabilities": 250000,
    "net_worth": 500000,
    "monthly_savings": 25000
  },
  "assets": [
    {
      "header": "Savings Account",
      "type": "Cash",
      "amount": 100000,
      "firm": "Bank A"
    }
  ],
  "liabilities": [
    {
      "header": "Home Loan",
      "type": "Mortgage",
      "outstanding_balance": 200000,
      "interest_rate": 5
    }
  ],
  "insurance": [
    {
      "product_name": "Life Insurance",
      "policy_type": "Term",
      "sum_assured": 500000,
      "premium": 5000
    }
  ],
  "goals": [
    {
      "name": "Retirement",
      "goal_type": "Retirement",
      "goal_amount": 1000000,
      "goal_year": 2040
    }
  ],
  "dependents": [
    {
      "first_name": "Jane",
      "relation": "Spouse"
    }
  ]
}
```

### GET `/api/usage` - Get Usage Statistics
Get token usage and cost tracking for all API calls.

**Response**:
```json
{
  "total": {
    "requests": 150,
    "tokens": 45000,
    "cost_usd": 0.225
  },
  "today": {
    "requests": 12,
    "tokens": 3600,
    "cost_usd": 0.018
  },
  "pricing": {
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25}
  }
}
```

### GET `/api/health` - Health Check
Check API and MongoDB connection status.

## MongoDB Schema

The application expects the following MongoDB schema structure:

### Collections Overview

1. **customers** - Primary customer data
   - FirstName, LastName, Email, PhoneNumber
   - DOB, Gender, Marital Status, Occupation
   - Earning, Expenses, Addresses
   - AgentId (references agents)

2. **Assets** - Customer assets
   - CustomerId, Header, Type
   - Amount, Firm

3. **liabilities** - Customer debts
   - CustomerId, Header, Type
   - OutstandingBalance, EMI, InterestRate

4. **insurance** - Insurance policies
   - CustomerId, PolicyNumber, ProductName
   - SumAssured, Premium, Status

5. **goal** - Financial goals
   - CustomerId, Name, GoalType
   - GoalAmount, GoalYear, CurrentAmount

6. **transactions** - Transaction history
   - CustomerId, Amount, Description
   - TransactionDate, Status

7. **callLogs** - Customer interaction history
   - CustomerId, CallDate, CallPurpose
   - CustomerSentiment, Notes

8. **dependents** - Customer family members
   - CustomerId, FirstName, Relation
   - DOB, Gender, Earning

9. **agents** - Bank advisors
   - username, first name, last name
   - email, phone, company, role

## Architecture

```
app/
├── main.py                 # FastAPI app with MongoDB lifecycle
├── api/
│   └── routes.py          # API endpoints with usage tracking
├── services/
│   ├── llm_service.py     # Claude integration with cost calculation
│   ├── query_service.py   # Query processing with MongoDB context
│   └── database_service.py # MongoDB queries & aggregation
├── models/
│   ├── query.py           # Request/response models
│   └── database.py        # Pydantic models for MongoDB collections
└── core/
    ├── config.py          # Configuration from environment
    └── database.py        # MongoDB connection management
```

## Cost Tracking

Costs are calculated based on Claude's pricing:

- **Claude 3 Sonnet**: $3/M input tokens, $15/M output tokens
- **Claude 3 Opus**: $15/M input tokens, $75/M output tokens  
- **Claude 3 Haiku**: $0.25/M input tokens, $1.25/M output tokens

Every API call returns detailed metrics including:
- Input/output token counts
- Individual and total costs
- Pricing rates per model

## Development

### Requirements
- Python 3.8+
- MongoDB 4.0+
- Claude API key
- All packages in `requirements.txt`

### Running Tests
```bash
pytest tests/ -v
```

### Next Steps for Production
1. Replace in-memory usage stats with MongoDB storage
2. Add authentication (JWT tokens)
3. Implement rate limiting
4. Add comprehensive logging
5. Set up monitoring and alerts
6. Add caching layer (Redis)
</content>
<parameter name="filePath">/Users/harshittiwari/Documents/Development/GenAdvisorIQ/README.md