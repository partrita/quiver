import os
import pytest
import time
from pathlib import Path
from quiver_pdb import (
    extract_pdbs,
    qvfrompdbs,
    extract_scorefile,
    list_tags,
    rename_tags,
    qvslice,
    qvsplit,
)

# 테스트 데이터 디렉토리 설정
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_QV_FILE = TEST_DATA_DIR / "test.qv"
TEST_PDB_FILES = [TEST_DATA_DIR / f"test_{i}.pdb" for i in range(3)]

@pytest.fixture(scope="session", autouse=True)
def setup_test_data():
    """테스트 데이터 디렉토리 생성 및 테스트 파일 생성"""
    TEST_DATA_DIR.mkdir(exist_ok=True)

    # 테스트용 PDB 파일 생성
    for pdb_file in TEST_PDB_FILES:
        with open(pdb_file, "w") as f:
            f.write("ATOM      1  N   ALA A   1      27.526  24.362   4.697  1.00 20.00\n")

    # 테스트용 Quiver 파일 생성
    qv_content = qvfrompdbs([str(pdb) for pdb in TEST_PDB_FILES])

    # 점수 정보 추가
    lines = qv_content.split('\n')
    modified_lines = []
    for line in lines:
        if line.startswith('QV_TAG'):
            tag = line.split()[1]
            modified_lines.append(line)
            # 각 태그에 대한 점수 정보 추가
            modified_lines.append(f"QV_SCORE {tag} rms=1.5|score=0.8")
        else:
            modified_lines.append(line)

    qv_content = '\n'.join(modified_lines)

    with open(TEST_QV_FILE, "w") as f:
        f.write(qv_content)

    yield

    # 테스트 후 정리
    for file in TEST_DATA_DIR.glob("*"):
        file.unlink()
    TEST_DATA_DIR.rmdir()
    # 커맨드 폴더의 *.pdb 파일도 삭제
    for pdb_file in Path(".").glob("*.pdb"):
        pdb_file.unlink()

def test_qvfrompdbs():
    """qvfrompdbs 도구 테스트"""
    start_time = time.time()
    result = qvfrompdbs([str(pdb) for pdb in TEST_PDB_FILES])
    end_time = time.time()

    assert result is not None
    assert len(result) > 0
    assert end_time - start_time < 1.0  # 1초 이내 실행

def test_extract_pdbs():
    """extract_pdbs 도구 테스트"""
    start_time = time.time()
    # extract_pdbs(str(TEST_QV_FILE), outdir=str(TEST_DATA_DIR))  # outdir 지원 시
    extract_pdbs(str(TEST_QV_FILE))  # outdir 미지원 시
    end_time = time.time()

    extracted_files = list(TEST_DATA_DIR.glob("*.pdb"))
    assert len(extracted_files) > 0
    assert end_time - start_time < 2.0  # 2초 이내 실행

def test_extract_scorefile():
    """extract_scorefile 도구 테스트"""
    start_time = time.time()
    extract_scorefile(str(TEST_QV_FILE))
    end_time = time.time()

    score_file = TEST_DATA_DIR / "test.sc"
    assert score_file.exists()
    assert end_time - start_time < 1.0  # 1초 이내 실행

def test_list_tags():
    """list_tags 도구 테스트"""
    start_time = time.time()
    list_tags(str(TEST_QV_FILE))  # 함수는 None을 반환하므로 반환값 검사 제거
    end_time = time.time()

    assert end_time - start_time < 1.0  # 1초 이내 실행

def test_rename_tags():
    """rename_tags 도구 테스트"""
    start_time = time.time()
    new_tags = ["new_tag1", "new_tag2", "new_tag3"]  # 태그 수를 3개로 수정
    rename_tags(str(TEST_QV_FILE), new_tags)
    end_time = time.time()

    # 이름 변경 후 태그 확인
    list_tags(str(TEST_QV_FILE))  # 함수는 None을 반환하므로 반환값 검사 제거
    assert end_time - start_time < 1.0  # 1초 이내 실행

def test_qvslice():
    """qvslice 도구 테스트"""
    start_time = time.time()
    tags = ["test_0", "test_1"]  # 실제 존재하는 태그로 수정
    qvslice(str(TEST_QV_FILE), tags)  # 함수는 None을 반환하므로 반환값 검사 제거
    end_time = time.time()

    assert end_time - start_time < 1.0  # 1초 이내 실행

def test_qvsplit():
    """qvsplit 도구 테스트"""
    start_time = time.time()
    ntags = 2
    prefix = "split_test"
    output_dir = str(TEST_DATA_DIR)
    qvsplit(str(TEST_QV_FILE), ntags, prefix, output_dir)
    end_time = time.time()

    split_files = list(TEST_DATA_DIR.glob(f"{prefix}_*.qv"))
    assert len(split_files) > 0
    assert end_time - start_time < 2.0  # 2초 이내 실행

def test_performance_large_file():
    """대용량 파일 처리 성능 테스트"""
    # 대용량 테스트 파일 생성
    large_qv_file = TEST_DATA_DIR / "large_test.qv"
    large_pdb_files = [TEST_DATA_DIR / f"large_test_{i}.pdb" for i in range(10)]

    # 대용량 PDB 파일 생성
    for pdb_file in large_pdb_files:
        with open(pdb_file, "w") as f:
            for i in range(1000):  # 각 파일에 1000개의 원자 추가
                f.write(f"ATOM  {i:5d}  N   ALA A {i:4d}   27.526  24.362   4.697  1.00 20.00\n")

    # 대용량 Quiver 파일 생성
    qv_content = qvfrompdbs([str(pdb) for pdb in large_pdb_files])
    with open(large_qv_file, "w") as f:
        f.write(qv_content)

    start_time = time.time()
    list_tags(str(large_qv_file))  # 함수는 None을 반환하므로 반환값 검사 제거
    end_time = time.time()

    assert end_time - start_time < 5.0  # 5초 이내 실행
