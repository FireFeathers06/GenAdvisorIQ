# app/models/database.py
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, List, Dict, Any
from bson import ObjectId

class PyObjectId(ObjectId):
    """Custom type for BSON ObjectId - Pydantic v2 compatible"""
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.with_info_plain_validator_function(cls.validate_objectid)
    
    @classmethod
    def validate_objectid(cls, v, info):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str):
            try:
                return ObjectId(v)
            except Exception:
                raise ValueError(f"Invalid ObjectId: {v}")
        raise ValueError(f"Invalid ObjectId type: {type(v)}")

# Agent Model
class Agent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    username: str
    first_name: str = Field(alias="first name")
    last_name: str = Field(alias="last name")
    password: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None


# Customer Model
class Customer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    first_name: str = Field(alias="FirstName")
    last_name: str = Field(alias="LastName")
    email: str = Field(alias="Email")
    phone_number: str = Field(alias="PhoneNumber")
    dob: str = Field(alias="DOB")
    gender: str = Field(alias="Gender")
    marital_status: str = Field(alias="Marital Status")
    occupation: str = Field(alias="Occupation")
    earning: int = Field(alias="Earning")
    expenses: Optional[int] = Field(None, alias="Expenses")
    permanent_address: str = Field(alias="PermanentAddress")
    communication_address: str = Field(alias="CommunicationAddress")
    agent_id: PyObjectId = Field(alias="AgentId")
    
    # Optional fields
    best_call_time: Optional[str] = Field(None, alias="bestCallTime")
    retirement_age: Optional[int] = Field(None, alias="RetirementAge")
    rpq: Optional[float] = None
    rpq_description: Optional[str] = Field(None, alias="rpqDescription")
    rpq_profile: Optional[str] = Field(None, alias="rpqProfile")
    persona: Optional[str] = None
    summary: Optional[str] = None


# Asset Model
class Asset(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    customer_id: PyObjectId = Field(alias="CustomerId")
    header: str = Field(alias="Header")
    type: str = Field(alias="Type")
    amount: int = Field(alias="Amount")
    firm: str = Field(alias="Firm")


# Liability Model
class Liability(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    customer_id: PyObjectId = Field(alias="CustomerId")
    header: str = Field(alias="Header")
    type: str = Field(alias="Type")
    outstanding_balance: int = Field(alias="OutstandingBalance")
    firm: str = Field(alias="Firm")
    emi: Optional[int] = Field(None, alias="EMI")
    interest_rate: Optional[int] = Field(None, alias="InterestRate")
    balance_term_years: Optional[int] = Field(None, alias="BalanceTerm(Years)")


# Insurance Model
class Insurance(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    customer_id: PyObjectId = Field(alias="CustomerId")
    policy_number: str = Field(alias="Policy Number")
    insurance_product: str = Field(alias="Insurance Product")
    product_name: str = Field(alias="Product Name")
    policy_type: str = Field(alias="Policy Type")
    premium: float = Field(alias="Premium")
    sum_assured: int = Field(alias="Sum Assured")
    status: str = Field(alias="Status")
    start_date: str = Field(alias="Start Date")
    end_date: str = Field(alias="End Date")
    due_date: str = Field(alias="Due Date")
    beneficiary: str = Field(alias="Beneficiary/Named Insured")


# Goal Model
class Goal(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    customer_id: PyObjectId = Field(alias="CustomerId")
    name: str = Field(alias="Name")
    goal_type: str = Field(alias="Goal Type")
    goal_amount: int = Field(alias="Goal Amount")
    current_amount: float = Field(alias="Current Amount yearmarked for the goal")
    goal_year: Optional[int] = Field(None, alias="Goal Year")
    age_at_goal: int = Field(alias="My Age at Year of Goal (Goal Year - DOB)")
    yes_no: str = Field(alias="Yes/No")
    
    # Optional fields
    down_payment: Optional[str] = None
    loan_tenure: Optional[str] = None


# Transaction Model
class Transaction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    customer_id: PyObjectId = Field(alias="CustomerId")
    amount: float = Field(alias="Amount")
    description: str = Field(alias="Description")
    transaction_date: str = Field(alias="TransactionDate")
    status: str = Field(alias="Status")
    recurring_status: str = Field(alias="RecurringStatus")


# CallLog Model
class CallLog(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    customer_id: PyObjectId = Field(alias="CustomerId")
    call_date: str = Field(alias="Call Date")
    call_time: str = Field(alias="Call Time")
    call_purpose: str = Field(alias="Call Purpose")
    status: str = Field(alias="Status (Opened/Closed)")
    customer_feedback: str = Field(alias="Customer Feedback")
    customer_sentiment: str = Field(alias="Customer Sentiment ")
    notes: str = Field(alias="Notes")


# Dependent Model
class Dependent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    customer_id: PyObjectId = Field(alias="CustomerId")
    first_name: str = Field(alias="FirstName")
    last_name: str = Field(alias="LastName")
    dob: str = Field(alias="DOB")
    gender: str = Field(alias="Gender")
    relation: str
    earning: Optional[str] = Field(None, alias="Earning")


# Global Variables Model
class GlobalVariables(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    inflation: float
    inflation_during_retirement: float = Field(alias="inflationDuringRetirement")
    investment_returns: float = Field(alias="investmentReturns")
    investment_returns_on_retirement_corpus: float = Field(alias="investmentReturnsOnRetirementCorpus")
    life_expectancy: int = Field(alias="lifeExpectancy")
    net_tax_on_investment_income: float = Field(alias="netTaxOnInvestmentIncome")
    percentage_drop_in_expenses: float = Field(alias="percentageDropInExpenses")
    retirement_age: int = Field(alias="retirementAge")
    tax_adjusted_returns: float = Field(alias="taxAdjustedReturns")
    
    @model_validator(mode='before')
    @classmethod
    def convert_decimals(cls, data):
        """Convert Decimal128 values to float"""
        if isinstance(data, dict):
            for key, value in data.items():
                if hasattr(value, 'to_decimal'):  # Decimal128
                    data[key] = float(value.to_decimal())
        return data


# API Usage Model
class ApiUsage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    endpoint: str
    method: str
    user_id: Optional[PyObjectId] = None  # Customer or Agent ID if applicable
    timestamp: str  # ISO format datetime
    status_code: int
    response_time_ms: Optional[float] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_size_bytes: Optional[int] = None
    response_size_bytes: Optional[int] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
