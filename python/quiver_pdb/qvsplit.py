#!/usr/bin/env python3
"""
Split a Quiver (.qv) file into multiple smaller Quiver files,
each containing a specified number of tags.

Usage:
    qvsplit.py mydesigns.qv 100
    → produces: split_000.qv, split_001.qv, ...
"""

import click
from quiver_pdb import rs_qvsplit


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
    click.secho(f"🔪 Splitting into chunks of {ntags} tags to '{output_dir}' with prefix '{prefix}'...", fg="cyan")

    try:
        # rs_qvsplit now returns a success message string.
        success_message = rs_qvsplit(file, ntags, prefix, output_dir)
        click.secho(success_message, fg="green") # The Rust message already includes "✅"
    except Exception as e:
        click.secho(f"❌ Error splitting Quiver file: {e}", fg="red", err=True)
        sys.exit(1) # Use sys.exit(1) for errors


if __name__ == "__main__":
    qvsplit()
