import click

from rich.console import Console

from fhnlab.cli.commands.cluster import cluster
from fhnlab.cli.commands.config import config
from fhnlab.cli.commands.experiment import experiment
from fhnlab.cli.commands.info import info
from fhnlab.cli.commands.solve import solve
from fhnlab.cli.commands.status import status
from fhnlab.cli.commands.validate import validate
from fhnlab.cli.commands.visualize import visualize

console = Console()


class FHNLabContext:
    """
    TODO: documentation
    """

    def __init__(self, verbose=False, configs_dir=None, data_dir=None):
        """
        TODO: documentation
        """

        self.verbose = verbose
        self.configs_dir = configs_dir
        self.data_dir = data_dir


@click.group()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Zapne podrobné logování. Enable verbose output.",
)
@click.option(
    "--configs-dir",
    type=click.Path(),
    default="~/.fhnlab/configs",
    help="Adresář s konfigurací. Path to configuration directory",
)
@click.option(
    "--data-dir",
    type=click.Path(),
    default="~/.fhnlab/data",
    help="Adresář s daty aplikace. Path to data directory",
)
@click.pass_context
def cli(ctx, verbose, configs_dir, data_dir):
    """
    FHNLab – FitzHugh–Nagumo Laboratory CLI.
    """

    ctx.obj = FHNLabContext(
        verbose=verbose,
        configs_dir=configs_dir,
        data_dir=data_dir,
    )

    if verbose:
        console.print("[bold green]Verbose mode enabled[/bold green]")


cli.add_command(cluster)
cli.add_command(config)
cli.add_command(experiment)
cli.add_command(info)
cli.add_command(solve)
cli.add_command(status)
cli.add_command(validate)
cli.add_command(visualize)
