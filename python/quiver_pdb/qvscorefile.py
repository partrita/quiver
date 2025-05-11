#!/usr/bin/env python3
"""
This script extracts the scorefile from a Quiver (.qv) file and writes it as a .csv file.

Usage:
    qvscorefile.py mydesigns.qv
"""

import sys
import click
from quiver_pdb import rs_extract_scorefile


@click.command()
@click.argument("qvfile", type=click.Path(exists=True, dir_okay=False))
def extract_scorefile(qvfile):
    """
    Extracts the scorefile from the provided Quiver file and saves it as a .csv file.
    """
    try:
        rs_extract_scorefile(qvfile)
    except Exception as e:
        click.secho(f"❌ Error: {str(e)}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    extract_scorefile()
