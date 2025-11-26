import click


@click.command()
@click.option("--config", default="config.yaml", help="Config file path.")
@click.pass_context
def solve(config="Empty"):
    """
    Run FitzHugh–Nagumo simulation. Solve the FitzHugh–Nagumo model.
    """

    click.echo("SOLVE — placeholder")
