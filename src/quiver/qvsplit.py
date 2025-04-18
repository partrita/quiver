#!/usr/bin/env python3
"""
This is a command-line tool to slice a specific set of tags from a Quiver file
into another Quiver file.

Usage:
    qvslice.py big.qv <tag1> <tag2> ... <tagN> > smaller.qv
"""

import os

from quiver import Quiver

import argparse


def main():
    """
    This is a command-line tool to split a Quiver file into multiple Quiver files
    with a specified number of tags per file.
    """

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Split a Quiver file into multiple Quiver files with a specified number of tags per file."
    )
    parser.add_argument("file", metavar="FILE", type=str, help="Quiver file to split")
    parser.add_argument(
        "ntags", metavar="NTAGS", type=int, help="Number of tags per file"
    )

    args = parser.parse_args()

    # Open the Quiver file
    q = Quiver(args.file, "r")

    # Split the file
    q.split(args.ntags, os.getcwd(), "split")


if __name__ == "__main__":
    main()
