#!/usr/bin/env python3
"""
This tool combines multiple PDB files into a Quiver-compatible stream.

Usage:
    qvfrompdbs.py <pdb1> <pdb2> ... <pdbN> > output.qv
"""

import os

# import sys
import click


@click.command()
@click.argument(
    "pdb_files", type=click.Path(exists=True, dir_okay=False), nargs=-1, required=True
)
def qv_from_pdbs(pdb_files):
    """
    Converts one or more PDB files into a Quiver-formatted stream.

    Output is printed to stdout.
    """
    for pdbfn in pdb_files:
        pdbtag = os.path.basename(pdbfn).removesuffix(".pdb")
        click.echo(f"QV_TAG {pdbtag}")
        with open(pdbfn, "r") as f:
            click.echo(f.read(), nl=False)


if __name__ == "__main__":
    qv_from_pdbs()
