# Quiver

This repository defines a type of file called a Quiver file. These files are simply one large file with the contents of many smaller files inside of them. Each entry has a unique name and can store meta_data about the entry.

There are several command line tools in this repository as well which enable the manipulation of Quiver files with composable (pipe-able) commands.

Quiver files and the different quiver tools are heavily influenced by Brian Coventry's silent_tools project. The difference is that Quiver files are able to work in environments outside of Rosetta which is very convenient.

## pytest

터미널에서 이 파일이 있는 디렉토리 또는 상위 프로젝트 루트에서 다음 명령어를 실행하세요:

```bash
pytest test_quiver_pytest.py
# 또는 단순히 (pytest가 테스트를 자동으로 찾음)
pytest
```
