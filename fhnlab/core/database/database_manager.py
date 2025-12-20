from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import select, and_, create_engine
from sqlalchemy.orm import Session, sessionmaker

from fhnlab.core.database.database import SessionLocal
from fhnlab.core.database.enums import (
    ExperimentStatus,
    ExecutionTarget,
    GeometryType,
    LogLevel,
)
from fhnlab.core.database.models.experiment import Experiment
from fhnlab.core.database.models.snapshot import Snapshot
from fhnlab.core.database.models.logs import ExperimentLog, SystemLog
from fhnlab.core.database.models.performance import PerformanceMetric
from fhnlab.core.database.models.sweep import ParameterSweep, ParameterSweepRun


class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, future=True)
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
        )

    def _session(self):
        return self.SessionLocal()

    def create_experiment(
        self,
        name: str,
        experiment_id: str,
        geometry_type: GeometryType,
        parameters: dict,
        geometry: dict | None = None,
        tags: list[str] | None = None,
        target: ExecutionTarget = ExecutionTarget.LOCAL,
    ) -> Experiment:
        with self._session() as session:
            exp = Experiment(
                name=name,
                experiment_id=experiment_id,
                status=ExperimentStatus.CREATED,
                target=target,
                geometry_type=geometry_type,
                parameters=parameters,
                geometry=geometry or {},
                tags=tags or [],
                created_at=datetime.utcnow(),
            )
            session.add(exp)
            session.commit()
            session.refresh(exp)

            return exp

    def get_experiment(self, experiment_id: int) -> Optional[Experiment]:
        with self._session() as session:
            return session.get(Experiment, experiment_id)

    def get_experiment_by_name(self, experiment_id: str) -> Optional[Experiment]:
        with self._session() as session:
            stmt = select(Experiment).where(Experiment.experiment_id == experiment_id)

            return session.scalar(stmt)

    def update_experiment_status(
        self,
        experiment_id: int,
        status: ExperimentStatus,
    ):
        with self._session() as session:
            exp = session.get(Experiment, experiment_id)

            if not exp:
                raise ValueError("Experiment not found")

            exp.status = status

            if status == ExperimentStatus.RUNNING:
                exp.started_at = datetime.utcnow()
            elif status in (
                ExperimentStatus.COMPLETED,
                ExperimentStatus.FAILED,
                ExperimentStatus.CANCELED,
            ):
                exp.finished_at = datetime.utcnow()

            session.commit()

    def search_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
        geometry_type: Optional[GeometryType] = None,
        target: Optional[ExecutionTarget] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Experiment]:
        with self._session() as session:
            conditions = []

            if status:
                conditions.append(Experiment.status == status)

            if geometry_type:
                conditions.append(Experiment.geometry_type == geometry_type)

            if target:
                conditions.append(Experiment.target == target)

            if date_from:
                conditions.append(Experiment.created_at >= date_from)

            if date_to:
                conditions.append(Experiment.created_at <= date_to)

            stmt = select(Experiment)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            return list(session.scalars(stmt))

    def add_snapshots(
        self,
        experiment_id: int,
        step: int,
        file_path: str,
    ):
        with self._session() as session:
            snap = Snapshot(
                experiment_id=experiment_id,
                step=step,
                file_path=file_path,
            )
            session.add(snap)
            session.commit()

    def get_snapshots(self, experiment_id: int) -> List[Snapshot]:
        with self._session() as session:
            stmt = select(Snapshot).where(Snapshot.experiment_id == experiment_id)

            return list(session.scalars(stmt))

    def log_experiment(
        self,
        experiment_id: int,
        level: LogLevel,
        message: str,
    ):
        with self._session() as session:
            log = ExperimentLog(
                experiment_id=experiment_id,
                level=level,
                message=message,
            )
            session.add(log)
            session.commit()

    def log_system(
        self,
        level: LogLevel,
        component: str,
        message: str,
    ):
        with self._session() as session:
            log = SystemLog(
                level=level,
                component=component,
                message=message,
            )
            session.add(log)
            session.commit()

    def get_experiment_logs(
        self,
        experiment_id: int,
        level: Optional[LogLevel] = None,
    ) -> List[ExperimentLog]:
        with self._session() as session:
            stmt = select(ExperimentLog).where(
                ExperimentLog.experiment_id == experiment_id
            )

            if level:
                stmt = stmt.where(ExperimentLog.level == level)

            return list(session.scalars(stmt))

    def add_performance_metric(
        self,
        experiment_id: int,
        cpu_percent: float,
        memory_mb: float,
    ):
        with self._session() as session:
            metric = PerformanceMetric(
                experiment_id=experiment_id,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
            )
            session.add(metric)
            session.commit()

    def create_parameter_sweep(
        self,
        name: str,
        parameter_space: Dict[str, Any],
    ) -> ParameterSweep:
        with self._session() as session:
            sweep = ParameterSweep(
                name=name,
                parameter_space=parameter_space,
            )
            session.add(sweep)
            session.commit()
            session.refresh(sweep)

            return sweep

    def get_statistics(self) -> Dict[str, int]:
        with self._session() as session:
            return {
                "experiments": session.query(Experiment).count(),
                "snapshots": session.query(Snapshot).count(),
                "experiment_logs": session.query(ExperimentLog).count(),
                "system_logs": session.query(SystemLog).count(),
                "performance_metrics": session.query(PerformanceMetric).count(),
                "parameter_sweeps": session.query(ParameterSweep).count(),
            }
