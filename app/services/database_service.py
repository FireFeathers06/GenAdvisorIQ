# app/services/database_service.py
from bson import ObjectId
from app.core.database import mongodb
from app.models.database import (
    Customer, Agent, Asset, Liability, Insurance, Goal, 
    Transaction, CallLog, Dependent, GlobalVariables, ApiUsage
)
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for querying MongoDB collections"""

    @staticmethod
    def _convert_objectids(obj):
        """Recursively convert ObjectId values to strings for JSON serialization"""
        if isinstance(obj, dict):
            return {key: DatabaseService._convert_objectids(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [DatabaseService._convert_objectids(item) for item in obj]
        elif hasattr(obj, '__class__') and 'ObjectId' in str(type(obj)):
            return str(obj)
        else:
            return obj

    @staticmethod
    async def get_customer(customer_id: str) -> Optional[Customer]:
        """Get customer by ID"""
        try:
            db = mongodb.get_db()
            customer_doc = await db["customers"].find_one(
                {"_id": ObjectId(customer_id)}
            )
            if customer_doc:
                return Customer(**customer_doc)
            return None
        except Exception as e:
            logger.error(f"Error fetching customer: {str(e)}")
            return None

    @staticmethod
    async def get_agent(agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        try:
            db = mongodb.get_db()
            agent_doc = await db["agents"].find_one(
                {"_id": ObjectId(agent_id)}
            )
            if agent_doc:
                return Agent(**agent_doc)
            return None
        except Exception as e:
            logger.error(f"Error fetching agent: {str(e)}")
            return None

    @staticmethod
    async def get_customer_assets(customer_id: str) -> List[Asset]:
        """Get all assets for a customer"""
        try:
            db = mongodb.get_db()
            assets = []
            async for asset_doc in db["Assets"].find(
                {"CustomerId": ObjectId(customer_id)}
            ):
                assets.append(Asset(**asset_doc))
            return assets
        except Exception as e:
            logger.error(f"Error fetching assets: {str(e)}")
            return []

    @staticmethod
    async def get_customer_liabilities(customer_id: str) -> List[Liability]:
        """Get all liabilities for a customer"""
        try:
            db = mongodb.get_db()
            liabilities = []
            async for liability_doc in db["liabilities"].find(
                {"CustomerId": ObjectId(customer_id)}
            ):
                liabilities.append(Liability(**liability_doc))
            return liabilities
        except Exception as e:
            logger.error(f"Error fetching liabilities: {str(e)}")
            return []

    @staticmethod
    async def get_customer_insurance(customer_id: str) -> List[Insurance]:
        """Get all insurance policies for a customer"""
        try:
            db = mongodb.get_db()
            policies = []
            async for policy_doc in db["insurance"].find(
                {"CustomerId": ObjectId(customer_id)}
            ):
                policies.append(Insurance(**policy_doc))
            return policies
        except Exception as e:
            logger.error(f"Error fetching insurance: {str(e)}")
            return []

    @staticmethod
    async def get_customer_goals(customer_id: str) -> List[Goal]:
        """Get all goals for a customer"""
        try:
            db = mongodb.get_db()
            goals = []
            async for goal_doc in db["goal"].find(
                {"CustomerId": ObjectId(customer_id)}
            ):
                goals.append(Goal(**goal_doc))
            return goals
        except Exception as e:
            logger.error(f"Error fetching goals: {str(e)}")
            return []

    @staticmethod
    async def get_customer_transactions(customer_id: str, limit: int = 10) -> List[Transaction]:
        """Get recent transactions for a customer"""
        try:
            db = mongodb.get_db()
            transactions = []
            async for txn_doc in db["transactions"].find(
                {"CustomerId": ObjectId(customer_id)}
            ).limit(limit):
                transactions.append(Transaction(**txn_doc))
            return transactions
        except Exception as e:
            logger.error(f"Error fetching transactions: {str(e)}")
            return []

    @staticmethod
    async def get_customer_call_logs(customer_id: str, limit: int = 5) -> List[CallLog]:
        """Get recent call logs for a customer"""
        try:
            db = mongodb.get_db()
            logs = []
            async for log_doc in db["callLogs"].find(
                {"CustomerId": ObjectId(customer_id)}
            ).limit(limit):
                logs.append(CallLog(**log_doc))
            return logs
        except Exception as e:
            logger.error(f"Error fetching call logs: {str(e)}")
            return []

    @staticmethod
    async def get_customer_dependents(customer_id: str) -> List[Dependent]:
        """Get all dependents for a customer"""
        try:
            db = mongodb.get_db()
            dependents = []
            async for dependent_doc in db["dependents"].find(
                {"CustomerId": ObjectId(customer_id)}
            ):
                dependents.append(Dependent(**dependent_doc))
            return dependents
        except Exception as e:
            logger.error(f"Error fetching dependents: {str(e)}")
            return []

    @staticmethod
    async def get_global_variables() -> Optional[GlobalVariables]:
        """Get global financial variables"""
        try:
            db = mongodb.get_db()
            globals_doc = await db["globalVariables"].find_one()
            if globals_doc:
                return GlobalVariables(**globals_doc)
            return None
        except Exception as e:
            logger.error(f"Error fetching global variables: {str(e)}")
            return None

    @staticmethod
    async def get_customer_context(customer_id: str) -> Dict[str, Any]:
        """Get complete customer context (customer + all related data)"""
        try:
            customer = await DatabaseService.get_customer(customer_id)
            if not customer:
                return {"error": "Customer not found"}

            # Fetch all related data in parallel
            agent = await DatabaseService.get_agent(str(customer.agent_id))
            assets = await DatabaseService.get_customer_assets(customer_id)
            liabilities = await DatabaseService.get_customer_liabilities(customer_id)
            insurance = await DatabaseService.get_customer_insurance(customer_id)
            goals = await DatabaseService.get_customer_goals(customer_id)
            transactions = await DatabaseService.get_customer_transactions(customer_id, limit=5)
            call_logs = await DatabaseService.get_customer_call_logs(customer_id, limit=3)
            dependents = await DatabaseService.get_customer_dependents(customer_id)
            global_vars = await DatabaseService.get_global_variables()

            # Calculate totals
            total_assets = sum(asset.amount for asset in assets) if assets else 0
            total_liabilities = sum(liability.outstanding_balance for liability in liabilities) if liabilities else 0
            net_worth = total_assets - total_liabilities

            context = {
                "customer": customer.model_dump(exclude={"id"}) if customer else None,
                "agent": agent.model_dump(exclude={"id"}) if agent else None,
                "financial_summary": {
                    "total_assets": total_assets,
                    "total_liabilities": total_liabilities,
                    "net_worth": net_worth,
                    "monthly_income": customer.earning if customer else 0,
                    "monthly_expenses": customer.expenses if customer else 0,
                    "monthly_savings": (customer.earning - customer.expenses) if customer and customer.expenses else 0,
                },
                "assets": [asset.model_dump(exclude={"id"}) for asset in assets],
                "liabilities": [liability.model_dump(exclude={"id"}) for liability in liabilities],
                "insurance": [policy.model_dump(exclude={"id"}) for policy in insurance],
                "goals": [goal.model_dump(exclude={"id"}) for goal in goals],
                "recent_transactions": [txn.model_dump(exclude={"id"}) for txn in transactions],
                "recent_call_logs": [log.model_dump(exclude={"id"}) for log in call_logs],
                "dependents": [dep.model_dump(exclude={"id"}) for dep in dependents],
                "global_config": global_vars.model_dump(exclude={"id"}) if global_vars else None,
            }
            
            # Convert any remaining ObjectId values to strings for JSON serialization
            return DatabaseService._convert_objectids(context)
        except Exception as e:
            logger.error(f"Error getting customer context: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    async def get_all_customer_ids() -> List[str]:
        """Return all customer IDs in the database."""
        try:
            db = mongodb.get_db()
            ids = []
            async for doc in db["customers"].find({}, {"_id": 1}):
                ids.append(str(doc["_id"]))
            return ids
        except Exception as e:
            logger.error(f"Error fetching customer IDs: {e}")
            return []

    @staticmethod
    async def update_customer_summary(customer_id: str, summary: str) -> bool:
        """Overwrite the summary field on a customer document."""
        try:
            db = mongodb.get_db()
            result = await db["customers"].update_one(
                {"_id": ObjectId(customer_id)},
                # Store as datetime so MongoDB can do $lt comparisons in the due-check query
                {"$set": {"summary": summary, "summary_refreshed_at": datetime.utcnow()}},
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating customer summary {customer_id}: {e}")
            return False

    @staticmethod
    async def get_customers_due_for_summary_refresh(months: int = 3) -> List[str]:
        """
        Return IDs of customers whose summary has never been generated
        or was last generated more than `months` months ago.
        """
        try:
            from datetime import timedelta
            threshold = datetime.utcnow() - timedelta(days=months * 30)
            db = mongodb.get_db()
            ids = []
            async for doc in db["customers"].find(
                {"$or": [
                    {"summary_refreshed_at": {"$exists": False}},
                    {"summary_refreshed_at": {"$lt": threshold}},
                ]},
                {"_id": 1},
            ):
                ids.append(str(doc["_id"]))
            return ids
        except Exception as e:
            logger.error(f"Error fetching customers due for summary refresh: {e}")
            return []

    @staticmethod
    async def insert_api_usage(usage: ApiUsage) -> bool:
        """Insert API usage log into database"""
        try:
            db = mongodb.get_db()
            usage_dict = usage.model_dump(by_alias=True, exclude={"id"})
            result = await db["api_usage"].insert_one(usage_dict)
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error inserting API usage: {str(e)}")
            return False

    @staticmethod
    async def get_usage_stats() -> Dict[str, Any]:
        """Get API usage statistics"""
        try:
            db = mongodb.get_db()
            # Total stats
            total_pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_requests": {"$sum": 1},
                        "total_tokens": {"$sum": {"$ifNull": ["$tokens_used", 0]}},
                        "total_cost": {"$sum": {"$ifNull": ["$cost_usd", 0.0]}}
                    }
                }
            ]
            total_result = await db["api_usage"].aggregate(total_pipeline).to_list(length=1)
            total_stats = total_result[0] if total_result else {"total_requests": 0, "total_tokens": 0, "total_cost": 0.0}
            
            # Today's stats
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            today_pipeline = [
                {"$match": {"timestamp": {"$gte": today_start}}},
                {
                    "$group": {
                        "_id": None,
                        "requests_today": {"$sum": 1},
                        "tokens_today": {"$sum": {"$ifNull": ["$tokens_used", 0]}},
                        "cost_today": {"$sum": {"$ifNull": ["$cost_usd", 0.0]}}
                    }
                }
            ]
            today_result = await db["api_usage"].aggregate(today_pipeline).to_list(length=1)
            today_stats = today_result[0] if today_result else {"requests_today": 0, "tokens_today": 0, "cost_today": 0.0}
            
            return {**total_stats, **today_stats}
        except Exception as e:
            logger.error(f"Error getting usage stats: {str(e)}")
            return {
                "total_requests": 0, "total_tokens": 0, "total_cost": 0.0,
                "requests_today": 0, "tokens_today": 0, "cost_today": 0.0
            }
