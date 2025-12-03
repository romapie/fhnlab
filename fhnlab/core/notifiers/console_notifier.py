from rich.console import Console

from .base import Notifier

console = Console()


class ConsoleNotifier(Notifier):
    def notify(self, message: str):
        console.print(f"[bold green]{message}")
