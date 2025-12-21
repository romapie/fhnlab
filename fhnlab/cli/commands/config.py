import click
from rich.console import Console
from rich.panel import Panel

from pygments.lexers import YamlLexer
from rich.syntax import Syntax
import yaml

from fhnlab.utils.config_utils import parse_value, set_nested


console = Console()


@click.command()
@click.group()
@click.pass_context
def config(ctx):
    """
    Configuration managemnt. Manage configuration files
    """

    pass
    # click.echo("TODO: implement 'config'. CONFIG — placeholder")


@config.command()
@click.argument("experiment")
@click.argument("config_type")
@click.pass_context
def show(ctx, experiment, config_type):
    db = ctx.obj["db"]

    exp = db.get_experiment_by_name(experiment)
    config = exp.configs.get(config_type)

    if not config:
        raise click.ClickException(f"No config '{config_type}'")

    text = yaml.dump(config, sort_keys=False)
    syntax = Syntax(text, "yaml", theme="monokai", line_numbers=False)

    console.print(Panel(syntax, title=f"{experiment} | {config_type}", expand=False))


@config.command()
@click.argument("experiment")
@click.argument("config_type")
@click.option("-p", "--param", multiple=True)
@click.pass_context
def edit(ctx, experiment, config_type, param):
    db = ctx.obj["db"]
    exp = db.get_experiment_by_name(experiment)

    cfg = exp.configs.get(config_type)
    if not cfg:
        raise click.ClickException("Config not found")

    for p in param:
        key, value = p.split("=", 1)
        set_nested(cfg, key, parse_value(value))

    db.update_experiment_config(exp.id, config_type, cfg)
    db.log_system("INFO", f"Config updated: {experiment}")

    console.print("[green]Config updated successfully[/green]")


@config.command()
@click.argument("source")
@click.argument("target")
@click.pass_context
def copy(ctx, source, target):
    db = ctx.obj["db"]

    src = db.get_experiment_by_name(source)
    new = db.create_experiment(
        name=target,
        geometry=src.geometry,
        configs=src.configs,
        tags=src.tags,
    )

    console.print(
        Panel(
            f"Copied configs from [bold]{source}[/] to [bold]{target}[/]",
            title="Config Copy",
        )
    )
