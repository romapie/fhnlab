from __future__ import annotations

from typing import Optional, Callable
from time import sleep

from .manager import ClusterManager


class SlurmManager:
    def __init__(self, manager: ClusterManager) -> None:
        self.mgr = manager

    # ------------------------------------------------------------
    # sbatch
    # ------------------------------------------------------------
    def submit_job(self, script_path: str) -> str:
        out = self.mgr.execute_command(f"sbatch {script_path}")
        # Expected: "Submitted batch job 123456"
        return out.split()[-1]

    # ------------------------------------------------------------
    # job status (squeue, sacct)
    # ------------------------------------------------------------
    def job_status(self, job_id: str) -> str:
        # Try squeue first
        out = self.mgr.execute_command(f"squeue -j {job_id} -h -o %T")
        if out:
            return out
        # If completed, use sacct
        out = self.mgr.execute_command(f"sacct -j {job_id} --format=State --noheader")
        return out.strip() or "UNKNOWN"

    # ------------------------------------------------------------
    # scancel
    # ------------------------------------------------------------
    def cancel_job(self, job_id: str):
        self.mgr.execute_command(f"scannel {job_id}")

    # ------------------------------------------------------------
    # wait_for_job()
    # ------------------------------------------------------------
    def wait_for_job(
        self,
        job_id: str,
        interval: int = 5,
        callback: Optional[Callable[[str], None]] = None,
    ):
        status = "UNKNOWN"

        while True:
            status = self.job_status(job_id)

            if callback:
                callback(status)

            if status in ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT"):
                return status

            sleep(interval)
