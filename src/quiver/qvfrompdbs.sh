#!/bin/bash

# This script takes a list of PDB files and generates a Quiver file from them
# Usage: qvfrompdbs.sh <pdb1> <pdb2> ... <pdbN> > mydesigns.qv

if [ $# -lt 1 ]; then
    echo "Usage: qvfrompdbs.sh <pdb1> <pdb2> ... <pdbN> > mydesigns.qv" >&2
    exit 1
fi

for pdbfn in "$@"; do
    if [ ! -f "$pdbfn" ]; then
        echo "File not found: $pdbfn" >&2
        exit 2
    fi
    pdbtag="${pdbfn##*/}"
    pdbtag="${pdbtag%.pdb}"
    printf "QV_TAG %s\n" "$pdbtag"
    cat "$pdbfn"
done
