#!/usr/bin/env python3
"""
This script extracts the scorefile from a Quiver (.qv) file and writes it as a .sc file.

Usage:
    qvscorefile.py mydesigns.qv
"""

import os
import sys
import click
import pandas as pd


@click.command()
@click.argument("qvfile", type=click.Path(exists=True, dir_okay=False))
def extract_scorefile(qvfile):
    """
    Extracts the scorefile from the provided Quiver file and saves it as a .sc file.
    """
    records = []

    with open(qvfile, "r") as qv:
        for line in qv:
            if line.startswith("QV_SCORE"):
                splits = line.split()
                tag = splits[1]

                try:
                    scores = {
                        entry[0]: float(entry[1])
                        for entry in (s.split("=") for s in splits[2].split("|"))
                    }
                except ValueError as e:
                    click.secho(
                        f"❌ Failed parsing scores for tag {tag}: {e}",
                        fg="red",
                        err=True,
                    )
                    continue

                scores["tag"] = tag
                records.append(scores)

    if not records:
        click.secho("❌ No score lines found in Quiver file.", fg="red", err=True)
        sys.exit(1)

    df = pd.DataFrame.from_records(records)

    outfn = os.path.splitext(qvfile)[0] + ".sc"
    df.to_csv(outfn, sep="\t", na_rep="NaN", index=False)

    click.secho(f"✅ Scorefile written to: {outfn}", fg="green")


if __name__ == "__main__":
    extract_scorefile()
