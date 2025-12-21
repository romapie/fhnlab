from fhnlab.core.database.enums import GeometryType

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from fhnlab.core.orchestrator.orchestrator import ExperimentOrchestrator
from fhnlab.core.database.enums import ExecutionTarget

console = Console()

GEOMETRY_MAP = {
    "line": GeometryType.LINE,
    "rect": GeometryType.RECTANGLE,
    "curve": GeometryType.CURVE,
    "surf": GeometryType.SURFACE,
}

TEMPLATES = {
    "spiral": {
        "epsilon": 0.08,
        "time": 300,
    },
    "wave": {
        "epsilon": 0.12,
        "time": 200,
    },
    "noise": {
        "epsilon": 0.2,
        "time": 100,
    },
}


@click.command()
@click.argument("geometry", type=click.Choice(GEOMETRY_MAP.keys()))
@click.argument("name")
@click.option("--template", type=click.Choice(TEMPLATES.keys()), default=None)
@click.option("--epsilon", type=float)
@click.option("--nx", type=int)
@click.option("--ny", type=int)
@click.option("--time", type=int)
@click.pass_context
def create(ctx, geometry, name, template, epsilon, nx, ny, time):
    """
    Create a new experiment.
    """

    orchestrator: ExperimentOrchestrator = ctx.obj["orchestrator"]

    geometry_type = GEOMETRY_MAP[geometry]

    # --- template base ---
    model_params = {}
    if template:
        model_params.update(TEMPLATES[template])

    # --- overrides ---
    if epsilon is not None:
        model_params["epsilon"] = epsilon
    if time is not None:
        model_params["time"] = time

    geometry_data = {}
    if geometry_type == GeometryType.RECT:
        geometry_data["nx"] = nx or 128
        geometry_data["ny"] = ny or 128

    # --- create experiment ---
    exp = orchestrator.create_experiment(
        name=name,
        geometry_type=geometry_type,
        geometry_data=geometry_data,
        model_params=model_params,
        tags=[template] if template else [],
        target=ExecutionTarget.LOCAL,
    )

    # --- Rich output ---
    table = Table(show_header=False)
    table.add_row("Name", exp.name)
    table.add_row("Geometry", geometry_type.value)
    table.add_row("Template", template or "custom")
    table.add_row("Status", exp.status.value)
    table.add_row("Experiment ID", exp.experiment_id)

    console.print(Panel(table, title="Experiment created", expand=False))

    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  fhnlab solve {name}")
    console.print(f"  fhnlab show {name}")
