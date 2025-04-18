# Quiver

This repository defines a type of file called a Quiver file. These files are simply one large file with the contents of many smaller files inside of them. Each entry has a unique name and can store meta_data about the entry.

There are several command line tools in this repository as well which enable the manipulation of Quiver files with composable (pipe-able) commands.

Quiver files and the different quiver tools are heavily influenced by Brian Coventry's silent_tools project. The difference is that Quiver files are able to work in environments outside of Rosetta which is very convenient.

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

# slice
qvslice big.qv <tag1> <tag2> ... <tagN> > smaller.qv
```

## 코드 테스트

터미널에서 이 파일이 있는 디렉토리 또는 상위 프로젝트 루트에서 다음 명령어를 실행하세요:

```bash
pytest test_quiver_pytest.py
# 또는 단순히 (pytest가 테스트를 자동으로 찾음)
pytest
```

## 할일

- [x] pytest 파일 만들기
- [ ] 코드 리팩토링하기
