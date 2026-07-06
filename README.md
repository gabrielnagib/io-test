# Simple Disk I/O Performance Tester

A lightweight, multi-threaded disk performance tester written in Python. It benchmarks disk read and write performance by writing and reading files of multiple sizes sequentially using thread pools.

## Features

- **Multi-threaded Benchmarking**: Uses Python's `ThreadPoolExecutor` for concurrent operations to evaluate multi-threaded disk performance.
- **Mid-size Distribution**: Given a target size, the script generates equal distributions of files at:
  - `size / 2` (Small files)
  - `size` (Mid-size files)
  - `size * 2` (Large files)
- **Zero CPU Bottleneck**: Buffers of random data are pre-generated to avoid timing CPU/memory generation overhead during disk I/O metrics.
- **Precision Metrics**: Computes exact throughput (MB/s), IOPS, average latency, and 95th-percentile (P95) latency using high-resolution performance timers.
- **Cross-Platform Drive Testing**: Supports benchmarking specific drives (e.g., secondary SSDs) and exits immediately with an error if the drive doesn't exist or is not writable.

---

## Installation

This utility has zero external dependencies. It requires **Python 3.8+**.

Clone or copy the files to your directory and run:

```bash
python app.py --help
```

---

## Usage

```bash
usage: app.py [-h] [--threads THREADS] [--n N] [--size SIZE] [--mode {write,read,both}] [--dir DIR] [--drive DRIVE]

Advanced Disk I/O Performance Tester

options:
  -h, --help            show this help message and exit
  --threads THREADS     Number of worker threads (default: 1)
  --n N                 Number of files to process (default: 1)
  --size SIZE           Size of each file in bytes (default: 4096)
  --mode {write,read,both}
                        Test mode (default: both)
  --dir DIR             Directory to use for testing (required for 'read' mode if not using 'both')
  --drive DRIVE         Drive/Path to test (default: 'D' on Windows, system default temp on Linux/macOS)
```

### Dynamic Platform Defaults
- **Windows**: Defaults to `--drive D`. If your system lacks a `D:` drive or it is read-only, the script outputs a clear error message and exits with status `1`.
- **Linux / macOS**: Defaults to the standard system temporary directory (e.g. `/tmp`). You can pass custom mount-points such as `--drive /mnt/ssd` to benchmark external storage.

---

## Examples

### 1. Default Run (1 thread, 1 file, 4KB mid-size on drive D)
```bash
python app.py
```

### 2. Multi-threaded benchmark with 6 files of 1MB mid-size on drive D
Generates exactly:
- 2 files of 512 KB (`size / 2`)
- 2 files of 1 MB (`size`)
- 2 files of 2 MB (`size * 2`)
```bash
python app.py --threads 4 --n 6 --size 1048576
```

### 3. Testing an external drive mount on macOS/Linux
```bash
python app.py --threads 8 --n 300 --size 65536 --drive /Volumes/ExternalSSD
```

### 4. Read-only test on an existing directory
```bash
python app.py --threads 4 --mode read --dir ./existing_test_data
```

---

## Output Metrics

The script reports detailed statistics for read and write tasks separately:

- **Files processed**: Total successful operations.
- **Total data**: Real data payload transferred in Megabytes.
- **Elapsed time**: Time taken for execution.
- **Throughput**: Overall transfer speed in MB/s.
- **IOPS**: Input/Output Operations Per Second.
- **Avg Latency**: Average time per request in milliseconds.
- **P95 Latency**: 95th-percentile latency to identify performance spikes/stuttering.
