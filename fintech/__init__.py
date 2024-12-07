from enum import Enum
import tomllib
from typing import Any, NoReturn
from flask import Flask, redirect, url_for
import click
import os
from flask.cli import FlaskGroup
import sys

from jinja2 import TemplateError
from werkzeug import Response


title = '''

███████╗██╗███╗   ██╗████████╗███████╗ ██████╗██╗  ██╗     ██████╗██╗     ██╗
██╔════╝██║████╗  ██║╚══██╔══╝██╔════╝██╔════╝██║  ██║    ██╔════╝██║     ██║
█████╗  ██║██╔██╗ ██║   ██║   █████╗  ██║     ███████║    ██║     ██║     ██║
██╔══╝  ██║██║╚██╗██║   ██║   ██╔══╝  ██║     ██╔══██║    ██║     ██║     ██║
██║     ██║██║ ╚████║   ██║   ███████╗╚██████╗██║  ██║    ╚██████╗███████╗██║
╚═╝     ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝     ╚═════╝╚══════╝╚═╝

'''


def ensure_configuration_availability(instance_path: str) -> str:
    if not os.path.exists(instance_path):
        try:
            os.makedirs(instance_path)
        except Exception as e:
            click.echo(click.style(f"Cannot create instance directory.\n{str(e)}", fg='red', bold=True))
            sys.exit()
    profile = os.getenv('PROFILE', 'Deployment')
    abs_config_path = os.path.join(instance_path, profile+'.toml')
    if not os.path.exists(abs_config_path):
        click.echo(click.style(f"The configuration file '{profile}.toml' is missing at {instance_path}.", fg='red', bold=True), nl=False)
        click.echo(click.style("Provide explicit configuration file to run application.", underline=True, fg='red', bold=True))
        sys.exit()
    return profile+'.toml'


def make_app() -> Flask:
    application = Flask(__name__, instance_relative_config=True)
    config_file = ensure_configuration_availability(application.instance_path)
    application.config.from_file(config_file, load=tomllib.load, text=False)

    from .blueprints import admin
    application.register_blueprint(admin.bp)

    application.cli.add_command(test)

    @application.get('/')
    def home() -> Response:
        return redirect(url_for('Admin.home'))

    @application.context_processor
    def admin_template_context_processor() -> dict[str, Any]:
        def raise_error(msg: str) -> NoReturn:
            raise TemplateError(msg)
        return dict(raise_error=raise_error)

    click.echo(click.style(title, fg='green'))
    return application


@click.group(cls=FlaskGroup, create_app=make_app)
def cli() -> None:
    """The CLI to interact with this application."""

@click.command()
def test() -> None:
    """Run tests.
    """        
    from fintech.tests import test as t 
    t.run()


class PatternTypes(Enum):
    HS = 'Head-&-Shoulders'
    IHS = 'Inverse Head-&-Shoulders'
    DB = 'Double Bottom'
    TB = 'Tripple Bottom'