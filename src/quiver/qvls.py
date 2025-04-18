#!/usr/bin/env python3
"""
This is a command-line tool to list all the tags in a Quiver file.

Usage:
    qvls.py <quiver_file>
"""

import click
from quiver import Quiver


@click.command()
@click.argument("quiver_file", type=click.Path(exists=True, dir_okay=False))
def list_tags(quiver_file):
    """
    List all tags in the given Quiver file.
    """
    qv = Quiver(quiver_file, "r")
    for tag in qv.get_tags():
        click.echo(tag)


if __name__ == "__main__":
    list_tags()
