# fhnlab/cli/__init__.py

import click

@click.group()
def cli():
    """FHNLab – FitzHugh–Nagumo Laboratory CLI."""
    pass


@cli.command()
def run():
    """Run simulation."""
    click.echo("Running FitzHugh–Nagumo simulation...")


@cli.command()
def info():
    """Show information about the project."""
    click.echo("FHNLab version 0.1.0 by romapie.")


def main():
    """Main entry point for the CLI."""
    cli()
