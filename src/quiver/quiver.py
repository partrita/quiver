#!/usr/bin/env python3
"""
This file defines the Quiver file class which is used to store PDB files and their associated scores.
This class is going to be the simplest and quickest implementation of a database for the PDB files and their scores.
This Quiver implementation will be just a list of PDB lines in a single file, with a tag for each PDB file.

Later this can be made more sophisticated by using a proper database, but for now this will be the simplest implementation.
"""

import os


class Quiver:
    def __init__(self, filename, mode, backend="txt"):
        if mode not in ("r", "w"):
            raise ValueError(
                f"Quiver file must be opened in 'r' or 'w' mode, not '{mode}'"
            )
        self.mode = mode
        self.fn = filename
        self.backend = backend
        self.tags = self._read_tags()

    def _read_tags(self):
        if not os.path.exists(self.fn):
            return []
        with open(self.fn, "r") as f:
            return [line.split()[1] for line in f if line.startswith("QV_TAG")]

    def get_tags(self):
        return list(self.tags)

    def size(self):
        return len(self.tags)

    def add_pdb(self, pdb_lines, tag, score_str=None):
        if self.mode != "w":
            raise RuntimeError(
                "Quiver file must be opened in write mode to allow for writing."
            )
        if tag in self.tags:
            raise ValueError(f"Tag {tag} already exists in this file.")

        with open(self.fn, "a") as f:
            f.write(f"QV_TAG {tag}\n")
            if score_str is not None:
                f.write(f"QV_SCORE {tag} {score_str}\n")
            f.writelines(pdb_lines)
            if pdb_lines and not pdb_lines[-1].endswith("\n"):
                f.write("\n")
        self.tags.append(tag)

    def get_pdblines(self, tag):
        if self.mode != "r":
            raise RuntimeError(
                "Quiver file must be opened in read mode to allow for reading."
            )

        with open(self.fn, "r") as f:
            found = False
            pdb_lines = []
            for line in f:
                if line.startswith("QV_TAG"):
                    current_tag = line.split()[1]
                    if current_tag == tag:
                        found = True
                        continue
                    elif found:
                        break
                if found:
                    if not line.startswith("QV_SCORE"):
                        pdb_lines.append(line)
            if not found:
                raise KeyError(f"Requested tag: {tag} does not exist")
            return pdb_lines

    def get_struct_list(self, tag_list):
        if self.mode != "r":
            raise RuntimeError(
                "Quiver file must be opened in read mode to allow for reading."
            )

        tag_set = set(tag_list)
        found_tags = []
        struct_lines = []
        write_mode = False

        with open(self.fn, "r") as f:
            for line in f:
                if line.startswith("QV_TAG"):
                    current_tag = line.split()[1]
                    write_mode = current_tag in tag_set
                    if write_mode:
                        found_tags.append(current_tag)
                if write_mode:
                    struct_lines.append(line)
        return "".join(struct_lines), found_tags

    def split(self, ntags, outdir, prefix):
        if self.mode != "r":
            raise RuntimeError(
                "Quiver file must be opened in read mode to allow for reading."
            )

        os.makedirs(outdir, exist_ok=True)
        file_idx = 0
        tag_count = 0
        out_file = None

        def open_new_file():
            nonlocal file_idx, out_file
            if out_file:
                out_file.close()
            out_path = os.path.join(outdir, f"{prefix}_{file_idx}.qv")
            out_file = open(out_path, "w")
            file_idx += 1

        with open(self.fn, "r") as f:
            for line in f:
                if line.startswith("QV_TAG"):
                    if tag_count % ntags == 0:
                        open_new_file()
                    tag_count += 1
                if out_file:
                    out_file.write(line)
            if out_file:
                out_file.close()
