#!/usr/bin/env python3
"""
Split a Quiver (.qv) file into multiple smaller Quiver files,
each containing a specified number of tags.

Usage:
    qvsplit.py mydesigns.qv 100
    → produces: split_000.qv, split_001.qv, ...
"""

import click
from quiver import Quiver


@click.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.argument("ntags", type=int)
@click.option(
    "--prefix", default="split", help="Prefix for the output files (default: 'split')"
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, writable=True),
    default=".",
    help="Directory to save the split files (default: current directory)",
)
def qvsplit(file, ntags, prefix, output_dir):
    """
    Split a Quiver FILE into multiple files, each with NTAGS tags.
    """
    if ntags <= 0:
        click.secho("❌ NTAGS must be a positive integer.", fg="red", err=True)
        raise click.Abort()

    click.secho(f"📂 Reading: {file}", fg="blue")
    click.secho(f"🔪 Splitting into chunks of {ntags} tags...", fg="green")

    q = Quiver(file, "r")
    q.split(ntags, output_dir, prefix)

    click.secho(f"✅ Files written to {output_dir} with prefix '{prefix}'", fg="green")


if __name__ == "__main__":
    qvsplit()
