# Quiver

This repository introduces and defines a specialized file format known as a **Quiver file**. A Quiver file acts as a container that consolidates the contents of many individual files into a single, structured file. Each piece of data within a Quiver file is referred to as an **entry**, and every entry is uniquely identified by a name. Along with the actual file contents, each entry can also include **metadata**, such as file size, timestamps, tags, or other descriptive information relevant to the entry. This format enables efficient storage, organization, and retrieval of a large number of related files within a single archive-like structure.

In addition to the file format itself, this repository provides a suite of **command-line tools** designed to interact with and manipulate Quiver files. These tools are built with a composable design philosophy in mind, meaning they are intended to be **pipe-able** and easily combined in Unix-style workflows. This allows users to construct complex data manipulation pipelines by chaining together simple commands, making the tools flexible and script-friendly.

The concept and implementation of Quiver files and their associated tools are **heavily inspired by Brian Coventry’s _silent_tools_ project**, which serves a similar purpose for working with data within the Rosetta molecular modeling suite. However, a key distinction is that Quiver files are intentionally designed to be **platform-agnostic** and can be used in environments **outside of Rosetta**. This makes them especially valuable for more general-purpose data handling, sharing, and processing workflows across a broader range of scientific and software contexts.

## How to install

```bash
uv pip install quiver-pdb
```

## How to use

```bash
# make a quiver file
qvfrompdbs *.pdb > my.qv

# ask what's in a quiver file
qvls my.qv

# ask how many things are in a quiver file
qvls my.qv | wc -l

# extract all pdbs from a quiver file
qvextract my.qv

# extract the first 10 pdbs from a quiver file
qvls my.qv | head -n 10 | qvextractspecific my.qv

# extract a random 10 pdbs from a quiver file
qvls my.qv | shuf | head -n 10 | qvextractspecific my.qv

# extract a specific pdb from a quiver file
qvextractspecific my.qv name_of_pdb_0001

# produce a scorefile from a quiver file
qvscorefile my.qv

# combine qv files
cat 1.qv 2.qv 3.qv > my.qv

# ensure all pdbs in quiver file have unique names
qvls my.qv | qvrename my.qv > uniq.qv

# split a quiver file into groups of 100
qvsplit my.qv 100

# slice a quiver file
qvslice big.qv <tag1> <tag2> ... <tagN> > smaller.qv
```

## Test

터미널에서 이 파일이 있는 디렉토리 또는 상위 프로젝트 루트에서 다음 명령어를 실행하세요:

```bash
uv run pytest
```

## Benchmark

### pure python

```bash
uv run python test/benchmark.py
Time to create Quiver file: 0.2492 seconds
Time to list tags: 0.0591 seconds
Time to slice Quiver file (5 tags): 0.0610 seconds
Time to extract from sliced Quiver file (5 files): 0.0267 seconds
Time to extract all files (101 files): 0.9863 seconds
```
### rusting version

```bash
uv run python test/benchmark.py
Time to create Quiver file: 0.0468 seconds
Time to list tags: 0.0603 seconds
Time to slice Quiver file (5 tags): 0.0962 seconds
Time to extract from sliced Quiver file (5 files): 0.0281 seconds
Time to extract all files (101 files): 0.4660 seconds
```

# References

Thank you to Nathaniel Bennett for creating this original code(https://github.com/nrbennet/quiver).
