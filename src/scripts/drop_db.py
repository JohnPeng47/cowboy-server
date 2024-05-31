import src.config as config
import click
from src.database.core import engine


@click.group()
def cowboy_database():
    pass


@cowboy_database.command("drop")
def drop_database():
    """Drops all data in database."""
    from sqlalchemy_utils import database_exists, drop_database

    if database_exists(str(config.SQLALCHEMY_DATABASE_URI)):
        drop_database(str(config.SQLALCHEMY_DATABASE_URI))


drop_database()
