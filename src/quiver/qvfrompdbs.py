import sys
import os


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: qvfrompdbs <pdb1> <pdb2> ... <pdbN> > mydesigns.qv", file=sys.stderr
        )
        sys.exit(1)

    for pdbfn in sys.argv[1:]:
        pdbtag = os.path.basename(pdbfn).replace(".pdb", "")
        print(f"QV_TAG {pdbtag}")
        with open(pdbfn, "r") as f:
            print(f.read(), end="")


if __name__ == "__main__":
    main()
