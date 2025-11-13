from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base

class ModelSubstitution(Base):
    __tablename__ = "model_substitutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=False)
    substitute_model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=False)
    valid_from = Column(DateTime, default=func.now())
    valid_to = Column(DateTime, nullable=True)
