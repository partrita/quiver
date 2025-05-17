#!/usr/bin/env python3
"""
This script benchmarks the speed of various functions in the provided code.
It focuses on measuring the execution time of key operations.
"""

import time
import os
import glob
import subprocess
import pathlib
import random
import sys
import shutil

# 현재 스크립트의 디렉토리
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = os.path.join(parent_dir, "python")
if os.path.isdir(src_dir):
    sys.path.insert(0, src_dir)
else:
    sys.path.insert(0, parent_dir)


def measure_time(func, *args, **kwargs):
    """Measures the execution time of a given function."""
    start_time = time.perf_counter()
    func(*args, **kwargs)
    end_time = time.perf_counter()
    return end_time - start_time


def create_test_quiver_file(basedir, tmp_path, input_pdb_files):
    """Creates a test Quiver file using qvfrompdb.py."""
    if not input_pdb_files:
        raise ValueError("No input PDB files found.")

    qv_path = tmp_path / "test_benchmark.qv"
    qvfrompdb_script = os.path.join(parent_dir, "python", "quiver_pdb", "qvfrompdb.py")
    
    if not os.path.exists(qvfrompdb_script):
        raise FileNotFoundError(f"Script not found: {qvfrompdb_script}")

    cmd = [sys.executable, qvfrompdb_script] + input_pdb_files
    try:
        with open(qv_path, "w") as f_out:
            subprocess.run(
                cmd,
                check=True,
                stdout=f_out,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
    except subprocess.CalledProcessError as e:
        print(f"Error running qvfrompdb.py: {e}")
        print(f"Stderr:\n{e.stderr}")
        raise
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Failed to run command. Is the script path correct? {e}"
        )

    if not qv_path.exists() or qv_path.stat().st_size == 0:
        raise IOError(f"Created Quiver file is empty or does not exist: {qv_path}")
    return qv_path


def list_quiver_tags(qv_file):
    """Lists tags from a Quiver file using qvls.py."""
    qvls_script = os.path.join(parent_dir, "python", "quiver_pdb", "qvls.py")
    if not os.path.exists(qvls_script):
        raise FileNotFoundError(f"Script not found: {qvls_script}")

    cmd = [sys.executable, qvls_script, str(qv_file)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    tags = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return tags


def slice_quiver_file(input_qv_file, tags_to_slice, output_qv_file):
    """Slices a Quiver file using qvslice.py."""
    slice_script = os.path.join(parent_dir, "python", "quiver_pdb", "qvslice.py")
    if not os.path.exists(slice_script):
        raise FileNotFoundError(f"Script not found: {slice_script}")

    tags_str = "\n".join(tags_to_slice)
    cmd = [sys.executable, slice_script, str(input_qv_file)]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=open(output_qv_file, "w"),  # 표준 출력을 파일로 리디렉션
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate(input=tags_str)
    if process.returncode != 0:
        print(f"Error running qvslice.py: {stderr}")
        raise subprocess.CalledProcessError(
            process.returncode, process.args, stdout, stderr
        )


def extract_from_quiver(qv_file, output_dir):
    extract_script = os.path.join(parent_dir, "python", "quiver_pdb", "qvextract.py")
    if not os.path.exists(extract_script):
        raise FileNotFoundError(f"Script not found: {extract_script}")

    abs_qv_file = os.path.abspath(qv_file)
    cmd = [sys.executable, extract_script, abs_qv_file]
    result = subprocess.run(
        cmd, check=False, cwd=output_dir, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error running qvextract.py: {result.stderr}")
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )


def main():
    """Main function to run the benchmarks."""
    basedir = parent_dir  # Project root directory
    benchmark_dir = pathlib.Path("./benchmark_temp")
    benchmark_dir.mkdir(exist_ok=True)
    input_pdb_dir = os.path.join(basedir, "tests", "input_for_tests")
    input_pdb_files = glob.glob(os.path.join(input_pdb_dir, "*.pdb"))
    input_pdb_files = [os.path.abspath(f) for f in input_pdb_files]

    if not input_pdb_files:
        print("Warning: No input PDB files found for benchmarking.")
        return

    try:
        # Benchmark Quiver file creation
        creation_time = measure_time(
            create_test_quiver_file, basedir, benchmark_dir, input_pdb_files
        )
        print(f"Time to create Quiver file: {creation_time:.4f} seconds")
        test_qv_file = benchmark_dir / "test_benchmark.qv"

        # Benchmark listing tags
        if test_qv_file.exists() and test_qv_file.stat().st_size > 0:
            list_tags_time = measure_time(list_quiver_tags, test_qv_file)
            print(f"Time to list tags: {list_tags_time:.4f} seconds")

            # Benchmark slicing
            all_tags = list_quiver_tags(test_qv_file)
            if all_tags:
                num_to_slice = min(5, len(all_tags))
                selected_tags = random.sample(list(all_tags), num_to_slice)
                sliced_qv_path = benchmark_dir / "sliced_benchmark.qv"
                slice_time = measure_time(
                    slice_quiver_file, test_qv_file, selected_tags, sliced_qv_path
                )
                print(
                    f"Time to slice Quiver file ({num_to_slice} tags): {slice_time:.4f} seconds"
                )
                # Benchmark extraction from sliced file
                if sliced_qv_path.exists() and sliced_qv_path.stat().st_size > 0:
                    extract_sliced_dir = benchmark_dir / "extracted_sliced"
                    extract_sliced_dir.mkdir(exist_ok=True)
                    extract_sliced_time = measure_time(
                        extract_from_quiver,
                        str(sliced_qv_path.resolve()),
                        extract_sliced_dir,
                    )
                    print(
                        f"Time to extract from sliced Quiver file"
                        f" ({num_to_slice} files): {extract_sliced_time:.4f} seconds"
                    )

            # Benchmark full extraction
            extract_full_dir = benchmark_dir / "extracted_full"
            extract_full_dir.mkdir(exist_ok=True)
            extract_full_time = measure_time(
                extract_from_quiver, str(test_qv_file.resolve()), extract_full_dir
            )
            print(
                f"Time to extract all files"
                f" ({len(input_pdb_files)} files): {extract_full_time:.4f} seconds"
            )

    except Exception as e:
        print(f"An error occurred during benchmarking: {e}")
    finally:
        # Clean up temporary directory
        if benchmark_dir.exists():
            shutil.rmtree(benchmark_dir)


if __name__ == "__main__":
    main()