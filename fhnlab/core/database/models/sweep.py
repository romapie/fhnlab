from sqlalchemy import String, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fhnlab.core.database.database import Base


class ParameterSweep(Base):
    __tablename__ = "parameter_sweeps"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    parameter_space: Mapped[dict] = mapped_column(JSON)

    runs = relationship("ParameterSweepRun", back_populates="sweep")


class ParameterSweepRun(Base):
    __tablename__ = "parameter_sweep_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    sweep_id: Mapped[int] = mapped_column(ForeignKey("parameter_sweeps.id"))
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"))

    sweep = relationship("ParameterSweep", back_populates="runs")
