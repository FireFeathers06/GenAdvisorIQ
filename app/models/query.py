from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    customer_id: str = Field(
        ...,
        description="MongoDB ObjectId of the customer",
        json_schema_extra={"example": "507f1f77bcf86cd799439011"},
    )
    question: str = Field(
        ...,
        json_schema_extra={"example": "How can I optimize my investment portfolio for retirement?"},
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": "507f1f77bcf86cd799439011",
                "question": "What should be my investment strategy given my current financial situation?",
            }
        }
    )
