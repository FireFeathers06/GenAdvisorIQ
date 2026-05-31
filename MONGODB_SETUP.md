# GenAdvisorIQ MongoDB Integration - Quick Start Guide

## Overview

GenAdvisorIQ now integrates with MongoDB to provide personalized financial advice. The system fetches customer data from your MongoDB instance and uses it to enrich AI recommendations through Claude.

## Data Flow

```
Customer Request
    ↓
MongoDB Query (get full customer context)
    ↓
Build Enhanced Prompt (with customer data)
    ↓
Claude AI Analysis
    ↓
Return Personalized Advice + Metrics
```

## MongoDB Setup

### 1. Ensure Collections Exist

Your MongoDB should have these collections in the `genaibot` database:

```
genaibot/
├── customers (primary collection)
├── agents
├── Assets
├── liabilities
├── insurance
├── goal
├── transactions
├── callLogs
├── dependents
└── globalVariables
```

### 2. Check Collection Schema

Use MongoDB compass or CLI to verify your data:

```bash
# Connect to MongoDB
mongosh mongodb://localhost:27017/genaibot

# Check customers collection
db.customers.findOne()

# Verify indexes (optional but recommended)
db.customers.createIndex({ "_id": 1, "AgentId": 1 })
db.Assets.createIndex({ "CustomerId": 1 })
db.liabilities.createIndex({ "CustomerId": 1 })
```

## API Usage Examples

### 1. Get Financial Advice (Main Endpoint)

```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "507f1f77bcf86cd799439011",
    "question": "What is the best investment strategy for my retirement given my current financial situation?"
  }'
```

**Response:**
```json
{
  "answer": "Based on your financial profile with monthly income of $75,000 and current net worth of $500,000, I recommend the following strategy...",
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
      "total_cost": 0.012435
    }
  }
}
```

### 2. Get Customer Financial Profile

```bash
curl -X GET "http://localhost:8000/api/customer/507f1f77bcf86cd799439011"
```

**Response:**
```json
{
  "customer": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone_number": "+1-555-123-4567",
    "monthly_income": 75000,
    "monthly_expenses": 50000,
    "occupation": "Software Engineer",
    "marital_status": "Married",
    "persona": "Conservative Investor"
  },
  "agent": {
    "username": "agent_jane",
    "first_name": "Jane",
    "last_name": "Smith",
    "company": "BankCorp",
    "email": "jane@bankcorp.com"
  },
  "financial_summary": {
    "total_assets": 750000,
    "total_liabilities": 250000,
    "net_worth": 500000,
    "monthly_income": 75000,
    "monthly_expenses": 50000,
    "monthly_savings": 25000
  },
  "assets": [
    {
      "header": "Savings Account",
      "type": "Cash",
      "amount": 100000,
      "firm": "Bank A"
    },
    {
      "header": "Stock Portfolio",
      "type": "Equities",
      "amount": 300000,
      "firm": "Investment Broker"
    },
    {
      "header": "Real Estate",
      "type": "Property",
      "amount": 350000,
      "firm": "Primary Residence"
    }
  ],
  "liabilities": [
    {
      "header": "Home Loan",
      "type": "Mortgage",
      "outstanding_balance": 200000,
      "interest_rate": 5,
      "emi": 2500,
      "balance_term_years": 20
    },
    {
      "header": "Car Loan",
      "type": "Auto Loan",
      "outstanding_balance": 50000,
      "interest_rate": 7,
      "emi": 1000,
      "balance_term_years": 5
    }
  ],
  "insurance": [
    {
      "policy_number": "POL-2024-001",
      "product_name": "Term Life Insurance",
      "policy_type": "Term",
      "sum_assured": 500000,
      "premium": 5000,
      "status": "Active",
      "beneficiary": "Spouse"
    },
    {
      "policy_number": "POL-2024-002",
      "product_name": "Health Insurance",
      "policy_type": "Family",
      "sum_assured": 500000,
      "premium": 15000,
      "status": "Active",
      "beneficiary": "Self"
    }
  ],
  "goals": [
    {
      "name": "Retirement Planning",
      "goal_type": "Retirement",
      "goal_amount": 1000000,
      "current_amount": 250000,
      "goal_year": 2040,
      "age_at_goal": 60
    },
    {
      "name": "Child Education",
      "goal_type": "Education",
      "goal_amount": 200000,
      "current_amount": 50000,
      "goal_year": 2035,
      "age_at_goal": 55
    }
  ],
  "dependents": [
    {
      "first_name": "Jane",
      "last_name": "Doe",
      "relation": "Spouse",
      "gender": "Female",
      "dob": "1985-06-15"
    },
    {
      "first_name": "Tom",
      "last_name": "Doe",
      "relation": "Child",
      "gender": "Male",
      "dob": "2010-03-20"
    }
  ],
  "recent_transactions": [
    {
      "amount": 5000,
      "description": "Salary Credit",
      "transaction_date": "2024-03-15",
      "status": "Completed",
      "recurring_status": "Monthly"
    }
  ],
  "recent_call_logs": [
    {
      "call_date": "2024-03-10",
      "call_purpose": "Portfolio Review",
      "customer_sentiment": "Positive",
      "status": "Closed",
      "notes": "Customer satisfied with performance"
    }
  ]
}
```

### 3. Get Usage Statistics

```bash
curl -X GET "http://localhost:8000/api/usage"
```

**Response:**
```json
{
  "total": {
    "requests": 45,
    "tokens": 65000,
    "cost_usd": 0.285
  },
  "today": {
    "requests": 8,
    "tokens": 12000,
    "cost_usd": 0.045
  },
  "pricing": {
    "claude-3-opus-20240229": {
      "input": 15.0,
      "output": 75.0
    },
    "claude-3-sonnet-20240229": {
      "input": 3.0,
      "output": 15.0
    },
    "claude-3-haiku-20240307": {
      "input": 0.25,
      "output": 1.25
    }
  }
}
```

### 4. Health Check

```bash
curl -X GET "http://localhost:8000/api/health"
```

**Response:**
```json
{
  "status": "healthy",
  "api": "running",
  "mongodb": "connected"
}
```

## Running the Server

### Start the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Access Swagger Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Key Features

### 1. Automatic Context Building
- Fetches customer profile
- Queries related assets, liabilities, insurance, goals
- Includes dependent information
- Calculates financial summaries

### 2. Enhanced Prompts
The system builds rich prompts including:
- Customer demographics
- Financial metrics (income, expenses, net worth)
- Asset allocation
- Debt structure and rates
- Insurance coverage
- Financial goals
- Risk profile

### 3. Cost Tracking
Every response includes:
- Input/output token counts
- Per-call costs
- Daily totals
- All-time totals

### 4. Error Handling
- Validates customer IDs
- Checks for missing customers
- Handles MongoDB connection issues
- Returns meaningful error messages

## Troubleshooting

### MongoDB Connection Issues

```python
# Check connection in Python
from app.core.database import mongodb
await mongodb.connect_db()  # Should print: ✅ Connected to MongoDB successfully
```

### Customer Not Found

Make sure the ObjectId exists:
```bash
# In MongoDB shell
db.customers.find({ "_id": ObjectId("507f1f77bcf86cd799439011") })
```

### API Not Responding

Check logs for startup errors:
```bash
# Should see MongoDB connection message
# ✅ Connected to MongoDB successfully
```

## Production Considerations

1. **Use Environment Variables**: Ensure `MONGODB_URL` and `MONGODB_DATABASE` are set
2. **Database Authentication**: Use MongoDB username/password in connection string
3. **Connection Pooling**: Motor handles this automatically
4. **Query Optimization**: Add indexes to frequently queried fields
5. **Error Handling**: Implement comprehensive logging
6. **Rate Limiting**: Add rate limits for API endpoints
7. **Caching**: Consider caching customer profiles (Redis)

## Example: Building a Web Interface

```javascript
// React/Vue example
async function getFinancialAdvice(customerId, question) {
  const response = await fetch('http://localhost:8000/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer_id: customerId, question })
  });
  
  const data = await response.json();
  return data;
}

// Usage
const advice = await getFinancialAdvice('507f1f77bcf86cd799439011', 
  'How should I invest for retirement?');
```

## Next Steps

1. Deploy to production environment
2. Set up MongoDB backup strategy
3. Monitor API usage and costs
4. Add customer authentication
5. Implement request/response logging
6. Set up error alerting
7. Performance testing and optimization
