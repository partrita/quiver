#!/usr/bin/env python3
"""
This is a command-line tool to list all the tags in a Quiver file

Usage:
    qvls.py <quiver_file>
"""

import sys

from quiver import Quiver


def main():
    quiver_file = sys.argv[1]
    qv = Quiver(quiver_file, "r")
    for tag in qv.get_tags():
        print(f"{tag}")


if __name__ == "__main__":
    main()
