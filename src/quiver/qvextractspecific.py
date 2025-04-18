#!/usr/bin/env python3
"""
This is a command-line tool to extract a specific set of PDB files from a Quiver file.

Usage:
    qvextract.py <quiver_file> <tag1> <tag2> ...
"""

import sys
import os

from quiver import Quiver

import stat


def main():
    quiver_file = sys.argv[1]

    tag_buffers = []
    if stat.S_ISFIFO(os.stat("/dev/stdin").st_mode):
        tag_buffers += sys.stdin.readlines()
    tag_buffers += sys.argv[2:]

    tags = []
    for line in tag_buffers:
        line = line.strip()
        if len(line) == 0:
            continue
        sp = line.split(" ")
        for tag in sp:
            tags.append(tag)

    qv = Quiver(quiver_file, "r")

    for tag in tags:
        outfn = f"{tag}.pdb"

        if os.path.exists(outfn):
            print(f"File {outfn} already exists, skipping")
            continue

        try:
            lines = qv.get_pdblines(tag)
        except KeyError:
            print(f"Could not find tag {tag} in Quiver file, skipping")
            continue

        with open(outfn, "w") as f:
            for line in lines:
                f.write(line)

    print(f"Successfully extracted {len(tags)} PDB files from {quiver_file}")


if __name__ == "__main__":
    main()
