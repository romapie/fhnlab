import click


@click.command()
@click.pass_context
def info(ctx):
    """
    Show project information
    """

    click.echo("FHNLab v0.1.0 – by romapie. INFO — placeholder")
