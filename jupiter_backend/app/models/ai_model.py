from sqlalchemy import Column, String, Integer, Numeric, DateTime, JSON, Enum
from sqlalchemy.dialects.postgresql import ENUM
from app.database import Base
import enum
from sqlalchemy.sql import func

class AIModelStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    under_updation = "under_updation"

# NEW ENUM for cost calculation type
class CostCalculationType(str, enum.Enum):
    tokens = "tokens"
    request = "request"

class AIModel(Base):
    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    model_identifier = Column(String, nullable=False, unique=True)
    input_cost_per_1k_tokens = Column(Numeric(10, 6), default=0)
    output_cost_per_1k_tokens = Column(Numeric(10, 6), default=0)
    max_tokens = Column(Integer, default=4096)
    context_window = Column(Integer, default=8192)
    capabilities = Column(JSON, default={})
    status = Column(Enum(AIModelStatus, name="aimodelstatus"), default=AIModelStatus.active)
    endpoint = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # NEW COLUMNS
    request_cost = Column(Numeric(10, 6), default=0)
    cost_calculation_type = Column(
        Enum(CostCalculationType, name="costcalculationtype", create_type=True), # create_type=True ensures the ENUM type is created in DB
        default=CostCalculationType.tokens,
        nullable=False
    )