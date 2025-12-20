from sqlalchemy import String, Enum, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from fhnlab.core.database.database import Base
from fhnlab.core.database.enums import LogLevel


class ExperimentLog(Base):
    __tablename__ = "experiment_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experimnats.id"))
    level: Mapped[LogLevel] = mapped_column(Enum(LogLevel))
    message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    experiment = relationship("Experiment", back_populates="logs")


class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[LogLevel]
    component: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)
