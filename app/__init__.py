import tomllib
from flask import Flask
import click
import os
from flask.cli import FlaskGroup
import sys


title = '''
                           
                           
     █████╗ ██████╗ ██████╗      ██████╗██╗     ██╗
    ██╔══██╗██╔══██╗██╔══██╗    ██╔════╝██║     ██║
    ███████║██████╔╝██████╔╝    ██║     ██║     ██║
    ██╔══██║██╔═══╝ ██╔═══╝     ██║     ██║     ██║
    ██║  ██║██║     ██║         ╚██████╗███████╗██║
    ╚═╝  ╚═╝╚═╝     ╚═╝          ╚═════╝╚══════╝╚═╝
                                                   

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

    from .blueprints import blog, admin
    application.register_blueprint(blog.bp)
    application.register_blueprint(admin.bp)

    application.cli.add_command(test)

    click.echo(click.style(title, fg='green'))
    return application


@click.group(cls=FlaskGroup, create_app=make_app)
def cli() -> None:
    """The CLI to interact with this application."""

@click.command()
def test() -> None:
    """Run tests.
    """        
    from app.tests import test as t 
    t.run()