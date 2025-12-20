from __future__ import annotations

import json
import subprocess
import shutil
import time
import threading
import psutil

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fhnlab.core.cluster.config import ClusterConfig  # type: ignore
from fhnlab.core.cluster.manager import ClusterManager  # type: ignore
from fhnlab.core.cluster.slurm import SlurmManager  # type: ignore
from fhnlab.core.notification_manager import NotificationManager  # type: ignore
from fhnlab.core.database.database_manager import DatabaseManager
from fhnlab.core.database.enums import ExperimentStatus, LogLevel


@dataclass
class ExperimentMetadata:
    experiment_id: str
    created_at: str
    backend: str
    job_id: Optional[str] = None
    status: str = "CREATED"
    host: Optional[str] = None
    runtime_seconds: Optional[float] = None
    notes: Optional[str] = None
    cost_estimate: Optional[Dict[str, Any]] = None


class ExperimentOrchestrator:
    """
    Orchestrates experiments: generation, local/cluster decision, execution,
    monitoring, result retrieval, metadata and notifications.
    """

    def __init__(
        self,
        database_url: str,
        solver,
        base_dir: Path,
        cluster_manager: Optional[ClusterManager] = None,
        slurm_manager: Optional[SlurmManager] = None,
        notifier: Optional[NotificationManager] = None,
        local_solver_cmd: str = "python3 -m fhnlab.solver",
        auto_cluster_thresholds: Optional[Dict[str, float]] = None,
    ):
        """
        :param base_dir: root directory where experiments will be created (local)
        :param cluster_manager: ClusterManager instance (for uploads/downloads)
        :param slurm_manager: SlurmManager instance (for submit/monitor)
        :param notifier: NotificationManager instance
        :param local_solver_cmd: command (prefix) to run local solver, must accept --config <path>
        :param auto_cluster_thresholds: thresholds to decide local vs. cluster (keys: grid_points, memory_gb, runtime_s)
        """
        self.base_dir = Path(base_dir).expanduser().resolve()
        self.cluster = cluster_manager
        self.slurm = slurm_manager
        self.notifier = notifier
        self.local_solver_cmd = local_solver_cmd
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.db = DatabaseManager(database_url)
        self.solver = solver

        # sensible defaults for decision logic if none provided
        self.thresholds = auto_cluster_thresholds or {
            "grid_points": 1_000_000,  # points
            "memory_gb": 4.0,  # GB
            "runtime_s": 3_600,  # seconds
        }

    # -------------------------
    # create_experiment
    # -------------------------
    def create_experiment(
        self,
        name: str,
        experiment_id: str,
        geometry_type,
        geometry: Dict[str, Any],
        params: Dict[str, Any],
        tags: list[str],
        target,
        job_template_render: Optional[str] = None,
    ) -> Path:
        """
        Create experiment directory and write config, geometry, slurm script (if provided).

        :param experiment_id: unique id string, e.g. "exp_0001"
        :param geoemtry: dict dict describing geoemtry
        :param params: dict of experiment parameters (time step, duration, etc.)
        :param job_template_render: optional string content of SLURM script (if available)
        :return: path to experiment directory
        """

        exp = self.db.create_experiment(
            name=name,
            geometry=geometry_type,
            geometry=geometry,
            parameters=params,
            tags=tags,
            target=target,
        )

        self.db.log_experiment(
            exp.id,
            LogLevel.INFO,
            "Experiment created",
        )

        exp_dir = self.base_dir / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        # create subfolders
        (exp_dir / "input").mkdir(exist_ok=True)
        (exp_dir / "output").mkdir(exist_ok=True)
        (exp_dir / "logs").mkdir(exist_ok=True)

        # write files
        with open(exp_dir / "geometry.json", "w", encoding="utf-8") as f:
            json.dump(geometry, f, indent=2)

        config = {"geometry": geometry, "params": params}
        with open(exp_dir / "config.json", "w", encoding="utf-8") as f:
            f.write(job_template_render)

        # initial metadata
        meta = ExperimentMetadata(
            experiment_id=experiment_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            backend="UNKNOWN",
        )
        self._save_metadata(exp_dir, meta)

        if self.notifier:
            self.notifier.notify_all(f"Experiment {experiment_id} created at {exp_dir}")

        return exp_dir and exp

    def solve_experiment(self, exp):
        self.db.update_experiment_status(exp.id, ExperimentStatus.RUNNING)

        self.db.log_experiment(
            exp.id,
            LogLevel.INFO,
            "Experiment started",
        )

        try:
            self._run_solver(exp)

            self.db.update_experiment_status(
                exp.id,
                ExperimentStatus.COMPLETED,
            )

            self.db.log_experiment(
                exp.id,
                LogLevel.INFO,
                "Experiment completed successfully",
            )
        except Exception as e:
            self.db.update_experiment_status(
                exp.id,
                ExperimentStatus.FAILED,
            )

            self.db.log_experiment(
                exp.id,
                LogLevel.ERROR,
                f"Experiment failed: {e}",
            )

            if self.notifier:
                self.notifier.error(str(e))

            raise

    # ---------------------------
    # estimate_computational_cost
    # ---------------------------
    def estimate_computational_cost(self, config: Dict[str, Any]) -> Dict[str, float]:
        """
        Estimate grid points, time steps, memory usage and runtime based on config.
        Heuristics only - tune to your solver.
        Returns dict with keys: grid_points, time_steps, memory_gb, runtime_estimate_s
        """
        # extract geometry info (expect keys like nx, ny, nz) - be tolerant.
        geom = config.get("geometry", {})
        nx = int(geom.get("nx", geom.get("nx", 1)))
        ny = int(geom.get("ny", geom.get("ny", 1)))
        nz = int(geom.get("nz", 1))

        grid_points = max(1, nx * ny * nz)

        params = config.get("params", {})
        duration = float(params.get("duration", 1.0))
        dt = float(params.get("dt", params.get("time_step", 1e-3)))
        time_steps = max(1, int(duration / dt))

        # very rough memory estimate: assume 8 bytes per variable * ~5 arrays + overhead
        per_points_bytes = 8 * 5
        memory_bytes = grid_points * per_points_bytes

        # account for time-snapshot buffers (e.g, storing some state)
        memory_bytes *= 1.2
        memory_gb = memory_bytes / (1024**3)

        # runtime heuristic: constant * grid_points * time_steps
        # tweak constant experimentally; here small default
        k = 0.00000005  # seconds per (point * step) - adjust to your solver profiling
        runtime_estimate_s = k * grid_points * time_steps

        return {
            "grid_points": grid_points,
            "time_steps": time_steps,
            "memory_gb": round(memory_gb, 3),
            "runtime_estimate_s": round(runtime_estimate_s, 3),
        }

    # ---------------------------
    # decide backend
    # ---------------------------
    def decide_backend(self, cost: Dict[str, float], mode: str = "auto") -> str:
        """
        Decide to run locally or on cluster based on heuristics and thresholds.
        mode: "auto" | "local" | "cluster"
        """

        if mode == "local":
            return "local"

        if mode == "cluster":
            return "cluster"

        # auto decision
        if (
            cost["grid_points"] > self.thresholds["grid_points"]
            or cost["memory_gb"] > self.thresholds["memory_gb"]
            or cost["runtime_estimate_s"] > self.thresholds["runtime_estimate_s"]
        ):
            return "cluster"

        return "local"

    # ---------------------------
    # _solve_locally wrapper
    # ---------------------------
    def _solve_locally(
        self, exp_dir: Path, config_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Run local solver as subprocess. Logs stdout/stderr into logs/ and returns metadata.
        """

        start_ts = time.time()
        cfg = config_path or (exp_dir / "config.json")
        log_out = exp_dir / "logs" / "stdout.log"
        log_err = exp_dir / "logs" / "stderr.log"

        cmd = f'{self.local_solver_cmd} --config "{cfg}"'

        if self.notifier:
            self.notifier.notify_all(f"Starting local solver for {exp_dir.name}: {cmd}")

        try:
            with open(log_out, "wb") as out_f, open(log_err, "wb") as err_f:
                proc = subprocess.run(
                    cmd, shell=True, stdout=out_f, stderr=err_f, check=False
                )
            exit_code = proc.returncode
            success = exit_code == 0
            status = "COMPLETED" if success else "FAILED"
        except Exception as exc:
            # unexpected erro running solver
            status = "FAILED"
            success = False

            if self.notifier:
                self.notifier.notify_all(f"Local solve failed: {exc}")

        end_ts = time.time()
        runtime = end_ts - start_ts

        # save metadata
        meta = ExperimentMetadata(
            experiment_id=exp_dir.name,
            created_at=datetime.utcnow().isoformat() + "Z",
            backend="local",
            job_id=None,
            status=status,
            runtime_seconds=runtime,
        )
        self._save_metadata(exp_dir, meta)

        if self.notifier:
            self.notifier.notify_all(
                f"Local run {exp_dir.name} finished: {status} (runtime {runtime:.1f}s)"
            )

        return {"status": status, "runtime_s": runtime}

    # ---------------------------
    # _solve_on_cluster
    # ---------------------------
    def _solve_on_cluster(
        self, exp_dir: Path, remote_base: str, remote_exp_subdir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload experiment folder to cluster, submit job, monitor and download results.
        remote_base: base directory on remote cluster to place experiment (e.g. '~/fhnlab')
        remote_exp_subdir: optional subdir name; if None will use exp_dir.name
        """

        if not self.cluster or not self.slurm:
            raise RuntimeError(
                "ClusterManager and SlurmManager must be provided for cluster runs."
            )

        start_ts = time.time()
        remote_subdir = remote_exp_subdir or exp_dir.name
        remote_dir = f"{remote_base.rstrip('/')}/{remote_subdir}"

        # 1. Upload directory
        if self.notifier:
            self.notifier.notify_all(f"Uploading {exp_dir} to {remote_dir} ...")

        try:
            self.cluster.upload_directory(str(exp_dir), remote_dir)
        except Exception as exc:
            if self.notifier:
                self.notifier.notify_all(f"Upload failed: {exc}")
            raise

        # 2. Submit
        # Prefer job.slurm in experiment dir, fallback to default job script name
        remote_job_script = f"{remote_dir}/job.slurm"
        try:
            job_id = self.slurm.submit_job(remote_job_script)
        except Exception as exc:
            if self.notifier:
                self.notifier.notify_all(f"Job submission failed: {exc}")
            raise

        # Update metadata early
        meta = ExperimentMetadata(
            experiment_id=exp_dir.name,
            created_at=datetime.utcnow().isoformat() + "Z",
            backend="cluster",
            job_id=str(job_id),
            status="SUBMITTED",
            host=self.cluster.config.host if hasattr(self.cluster, "config") else None,
        )
        self._save_metadata(exp_dir, meta)
        if self.notifier:
            self.notifier.notify_all(
                f"{job_id} submitted for experiment {exp_dir.name}"
            )

        # 3. Monitor job
        final_status = None
        try:

            def cb(status_str: str):
                # callback passed to wait_for_job; called periodically with status
                if self.notifier:
                    self.notifier.notify_all(f"Job {job_id} status: {status_str}")
                # also update metadata status frequently
                meta_now = ExperimentMetadata(
                    experiment_id=exp_dir.name,
                    created_at=meta.created_at,
                    backend="cluster",
                    job_id=str(job_id),
                    status=status_str,
                    host=meta.host,
                )
                self._save_metadata(exp_dir, meta_now)

            final_status = self.slurm.wait_for_job(str(job_id), interval=5, callback=cb)
        except Exception as exc:
            if self.notifier:
                self.notifier.notify_all(f"Error while monitoring job {job_id}: {exc}")
            raise

        # 4. After completion, download results
        if self.notifier:
            self.notifier.notify_all(
                f"Job {job_id} finished with status {final_status}. Dowloading results..."
            )
        try:
            self._download_results(remote_dir, exp_dir)
        except Exception as exc:
            if self.notifier:
                self.notifier.notify_all(f"Download failed: {exc}")
            raise

        end_ts = time.time()
        runtime = end_ts - start_ts

        # final metadata
        meta_final = ExperimentMetadata(
            experiment_id=exp_dir.name,
            created_at=meta.created_at,
            backend="cluster",
            job_id=str(job_id),
            status=final_status,
            host=meta.host,
            runtime_seconds=runtime,
        )
        self._save_metadata(exp_dir, meta_final)

        if self.notifier:
            self.notifier.notify_all(
                f"Experiment {exp_dir.name} finished on cluster: {final_status}"
            )

        return {"status": final_status, "job_id": job_id, "runtime_s": runtime}

    # -------------------------
    # _download_results
    # -------------------------
    def _download_results(self, remote_dir: str, local_dir: Path):
        """
        Download remote experiment dir (or results subfolder) into local_dir/output
        """

        if not self.cluster:
            raise RuntimeError("ClusterManager required to download results.")

        local_out = local_dir / "output"
        local_out.mkdir(parents=True, exist_ok=True)

        # Attempt recursive download of remote_dir/output -> local output
        # Many clusters will place results inside remote_dir/output
        remote_output = f"{remote_dir}/output"
        try:
            self.cluster.download_directory(remote_output, str(local_out))
        except Exception:
            # fallback: dowload whole remote_dir
            self.cluster.download_directory(remote_dir, str(local_dir))

    # -------------------------
    # check_job_status
    # -------------------------
    def check_job_status(self, job_id: str) -> str:
        """
        Return job status string using SlurmManager.
        """
        if not self.slurm:
            raise RuntimeError("SlurmManager required to check job status.")
        return self.slurm.job_status(job_id)

    # -------------------------
    # metadata_tracking
    # -------------------------
    def _save_metadata(self, exp_dir: Path, metadata: ExperimentMetadata):
        """
        Save job_info.json in experiment directory (overwrites).
        """

        out_path = exp_dir / "job_info.json"
        obj = asdict(metadata)
        # include timestamp of update
        obj["_update_at"] = datetime.utcnow().isoformat() + "Z"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)

    # -------------------------
    # Public run API
    # -------------------------
    def run_experiment(
        self,
        experiment_id: str,
        geoemtry: Dict[str, Any],
        params: Dict[str, Any],
        mode: str = "auto",
        remote_base: str = "~/fhnlab/experiments",
        job_template_render: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Top-level orchestrator API:
        - creates experiment folder and configs
        - estimates cost and decides backend
        - runs locally or on cluster
        - returns dict with final status and metadata
        """

        exp_dir = self.create_experiment(
            experiment_id, geoemtry, params, job_template_render
        )
        # load config from file for consistent estimation
        with open(exp_dir / "config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        cost = self.estimate_computational_cost(config)
        backend = self.decide_backend(cost, mode=mode)

        # write cost estimate into metadata
        meta = ExperimentMetadata(
            experiment_id=experiment_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            backend=backend,
            cost_estimate=cost,
        )
        self._save_metadata(exp_dir, meta)

        if self.notifier:
            self.notifier.notify_all(
                f"Experiment {experiment_id}: decided backend = {backend} (cost = {cost})"
            )

        if backend == "local":
            result = self._solve_locally(exp_dir)
        else:
            result = self._solve_on_cluster(exp_dir, remote_base)

        # final notification
        if self.notifier:
            self.notifier.notify_all(
                f"Experiment {experiment_id} final result: {result.get('status')}"
            )

        return {
            "experiment_id": experiment_id,
            "backend": backend,
            "cost": cost,
            **result,
        }

    def start_performance_monitor(self, exp_id, interval=2):
        self._perf_running = True

        def monitor():
            while self._perf_running:
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory().used / 1024 / 1024

                self.db.add_performance_metric(
                    exp_id,
                    cpu_percent=cpu,
                    memory_mb=mem,
                )
                time.sleep(interval)

        t = threading.Thread(target=monitor, daemon=True)
        t.start()

    def save_snapshot(self, exp, step, file_path):
        self.db.add_snapshot(
            experiment_id=exp.id,
            step=step,
            file_path=file_path,
        )

        self.db.log_experiment(
            exp.id,
            LogLevel.INFO,
            f"Snapshot saved at step {step}",
        )
