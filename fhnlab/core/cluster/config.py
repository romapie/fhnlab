from dataclasses import dataclass


@dataclass
class ClusterConfig:
    host: str
    user: str
    port: 22
    key_path: str | None = None
    password: str | None = None

    work_dir: str = "~/fhnlab"
    slurm_partition: str = "default"
    slurm_account: str | None = None
