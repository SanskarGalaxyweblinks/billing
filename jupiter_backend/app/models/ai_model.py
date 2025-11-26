from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from app.database import Base


class AIModelStatus(str, enum.Enum):
    """Lifecycle states for a base AI model."""

    active = "active"
    inactive = "inactive"
    under_updation = "under_updation"


class CostCalculationType(str, enum.Enum):
    """Cost strategies for billing a model."""

    tokens = "tokens"
    request = "request"


def _capabilities_default() -> Dict[str, Any]:
    return {}


class AIModel(Base):
    """
    Core SQLAlchemy model for managing base AI models that power the platform.

    Previously the file accidentally contained admin router logic and no longer
    defined the ORM entity. The absence of this definition caused FastAPI to
    crash when importing `app.models.ai_model`. This class reintroduces the
    database schema so other modules (usage logs, assignments, analytics, etc.)
    can function correctly.
    """

    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=False)
    model_identifier = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Pricing & costing
    input_cost_per_1k_tokens = Column(Numeric(12, 6), default=0, nullable=False)
    output_cost_per_1k_tokens = Column(Numeric(12, 6), default=0, nullable=False)
    request_cost = Column(Numeric(12, 6), default=0, nullable=False)
    cost_calculation_type = Column(
        SAEnum(CostCalculationType, name="ai_model_cost_type"),
        default=CostCalculationType.tokens,
        nullable=False,
    )

    # Capabilities & limits
    max_tokens = Column(Integer, nullable=True)
    context_window = Column(Integer, nullable=True)
    capabilities = Column(JSON, default=_capabilities_default, nullable=True)
    endpoint = Column(String(500), nullable=True)

    # Metadata
    status = Column(
        SAEnum(AIModelStatus, name="ai_model_status"),
        default=AIModelStatus.active,
        nullable=False,
    )
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_used_at = Column(DateTime, nullable=True)

    # ---------------------------------------------------------------------
    # Helper utilities
    # ---------------------------------------------------------------------

    def get_capabilities(self) -> Dict[str, Any]:
        """Return capabilities as a dictionary."""
        value = self.capabilities
        if value in (None, "", {}):
            return {}
        if isinstance(value, dict):
            return value
        # JSON columns may come back as strings depending on the driver
        try:
            import json

            return json.loads(value) if isinstance(value, str) else dict(value)
        except (ValueError, TypeError):
            return {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize model fields into a plain dictionary for responses."""

        def _to_float(val: Optional[Numeric]) -> float:
            return float(val or 0)

        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "model_identifier": self.model_identifier,
            "description": self.description,
            "input_cost_per_1k_tokens": _to_float(self.input_cost_per_1k_tokens),
            "output_cost_per_1k_tokens": _to_float(self.output_cost_per_1k_tokens),
            "request_cost": _to_float(self.request_cost),
            "cost_calculation_type": self.cost_calculation_type,
            "max_tokens": self.max_tokens,
            "context_window": self.context_window,
            "capabilities": self.get_capabilities(),
            "status": self.status,
            "endpoint": self.endpoint,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<AIModel id={self.id} name={self.name!r} provider={self.provider!r} status={self.status}>"