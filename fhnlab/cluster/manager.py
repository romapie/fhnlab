import os
import paramiko

from scp import SCPClient
from pathlib import Path
from typing import Optional

from .config import ClusterConfig


class ClusterManager:
    def __init__(self, config: ClusterConfig):
        self.config = config
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.scp_client: Optional[SCPClient] = None

    # ------------------------------------------------------------
    # SSH connect + key + password fallback
    # ------------------------------------------------------------
    def connect(self):
        if self.ssh_client is not None:
            return self.ssh_client

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_args = {
            "hostname": self.config.host,
            "username": self.config.user,
            "port": self.config.port,
        }

        # Prefer key authentication
        if self.config.key_path:
            connect_args["key_filename"] = self.config.key_path
        else:
            connect_args["password"] = self.config.password

        try:
            client.connect(**connect_args)
        except Exception as e:
            raise RuntimeError(f"SSH connection failed: {e}")

        self.ssh_client = client
        self.scp_client = SCPClient(client.get_transport(), progress=self._progress)
        return client

    def _progress(self, filename, size, sent):
        # This can be replaced with tqdm or rich later
        print(f"{filename}: {sent}/{size} bytes", end="\r")

    # ------------------------------------------------------------
    # Execute remote command
    # ------------------------------------------------------------
    def execute_command(self, command: str):
        if self.ssh_client is None:
            self.connect()

        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()

        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()

        if exit_code != 0:
            raise RuntimeError(f"Command failed ({exit_code}): {err}")

        return out

    # ------------------------------------------------------------
    # Upload file
    # ------------------------------------------------------------
    def upload_file(self, local_path: str, remote_path: str):
        if self.scp_client is None:
            self.connect()
        self.scp_client.put(local_path, remote_path)

    # ------------------------------------------------------------
    # Upload directory (rekurzivně)
    # ------------------------------------------------------------
    def upload_directory(self, local_dir: str, remote_dit: str):
        if self.scp_client is None:
            self.connect()

        local_dir = Path(local_dir)

        for root, dirs, files in os.walk(local_dir):
            relative = Path(root).relative_to(local_dir)
            remote_path = Path(remote_dit / relative).as_posix()

            # Create directory on cluster
            self.execute_command(f"mkdir -p {remote_path}")

            # Upload files
            for file in files:
                self.scp_client.put(
                    os.path.join(root, file), os.path.join(remote_path, file)
                )

    # ------------------------------------------------------------
    # Downland file + directory
    # ------------------------------------------------------------
    def download_file(self, remote_path: str, local_path: str):
        if self.scp_client is None:
            self.connect()
        self.scp_client.get(remote_path, local_path)

    def download_directory(self, remote_dir: str, local_dir: str):
        if self.scp_client is None:
            self.connect()

        os.makedirs(local_dir, exist_ok=True)

        # recursive download
        self.scp_client.get(remote_dir, local_dir, recursive=True)

    # ------------------------------------------------------------
    # Reconnect logic
    # ------------------------------------------------------------
    def ensure_connected(self):
        try:
            self.execute_command("echo ok")
        except Exception as e:
            print(e)
            print("Reconnecting...")
            self.ssh_client = None
            self.connect()

    def close(self):
        if self.ssh_client:
            self.ssh_client.close()
            self.scp_client = None


class ClusterPool:
    def __init__(self):
        self.connections = {}

    def get(self, config: ClusterConfig):
        key = (config.host, config.user, config.port)
        if key not in self.connections:
            self.connections[key] = ClusterManager(config)
            self.connections[key].connect()
        return self.connections[key]
