from sqlalchemy import String, DateTime, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from fhnlab.core.database.database import Base
from fhnlab.core.database.enums import ExperimentStatus, ExecutionTarget, GeometryType


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String, index=True)
    experiment_id: Mapped[str] = mapped_column(String, unique=True, index=True)

    status: Mapped[ExperimentStatus] = mapped_column(Enum(ExperimentStatus))
    target: Mapped[ExecutionTarget] = mapped_column(Enum(ExecutionTarget))

    geometry_type: Mapped[GeometryType]
    geometry_data: Mapped[dict] = mapped_column(JSON)

    parameters: Mapped[dict] = mapped_column(JSON)
    tags: Mapped[list[str]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]

    # relationships
    snapshots = relationship("Snapshot", back_populates="experiment")
    logs = relationship("ExperimentLog", back_populates="experiment")
    metrics = relationship("PerformanceMetric", back_populates="experiment")
