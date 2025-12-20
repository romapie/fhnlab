from sqlalchemy import Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from fhnlab.core.database.database import Base


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"))

    cpu_percent: Mapped[float]
    memory_mb: Mapped[float]
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    experiment = relationship("Experiment", back_populates="metrics")
