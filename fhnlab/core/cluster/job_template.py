from dataclasses import dataclass


@dataclass
class JobTemplate:
    job_name: str
    time_limit: str = "05:00:00"
    memory: str = "8G"
    cpus: int = 4
    partition: str = "default"
    mail_user: str | None = None
    mail_type: str = "ALL"
    modules: list[str] = None
    venv_path: str = "~/fhnlab/.venv"
    work_dir: str = "~/fhnlab"
    logs_dir: str = "logs"

    def render(self) -> str:
        script = "#!/bin/bash\n"
        script += f"#SBATCH --job-name={self.job_name}\n"
        script += f"#SBATCH --time={self.time_limit}\n"
        script += f"#SBATCH --mem={self.memory}\n"
        script += f"#SBATCH --cpus-per-task={self.cpus}\n"
        script += f"#SBATCH --partition={self.partition}\n"

        if self.mail_user:
            script += f"#SBATCH --mail-user={self.mail_user}\n"
            script += f"#SBATCH --mail-type={self.mail_type}\n"

        script += f"#SBATCH --output={self.logs_dir}/%x_%j.out\n"
        script += f"SBATCH --error={self.logs_dir}/%_%j.err\n"

        script += "\n"
        script += f"cd {self.work_dir}\n"
        script += "module load python/3.10\n"
        script += f"source {self.venv_path}/bin/activate\n"

        script += """
echo "START: $(date)"
hostname

python run.py

echo "END: $(date)"
"""

        return script
