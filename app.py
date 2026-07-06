import argparse
import os
import sys
import time
import tempfile
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

def generate_random_bytes(size: int) -> bytes:
    """Generates a buffer of random bytes."""
    return os.urandom(size)

def write_task(index: int, data: bytes, target_dir: Path) -> tuple[Path, float, int]:
    """Writes data to a file and returns the file path, time taken, and bytes written."""
    file_path = target_dir / f"test_file_{index}.bin"
    start = time.perf_counter()
    try:
        file_path.write_bytes(data)
        return file_path, time.perf_counter() - start, len(data)
    except Exception as e:
        raise RuntimeError(f"Write error at {file_path}: {e}")

def read_task(file_path: Path) -> tuple[float, int]:
    """Reads a file and returns the time taken and bytes read."""
    start = time.perf_counter()
    try:
        data = file_path.read_bytes()
        return time.perf_counter() - start, len(data)
    except Exception as e:
        raise RuntimeError(f"Read error at {file_path}: {e}")

def print_metrics(label: str, count: int, total_bytes: int, elapsed_time: float, latencies: list[float]):
    if elapsed_time <= 0:
        print(f"\n{label} metrics could not be calculated.")
        return

    mb_per_sec = (total_bytes / (1024 * 1024)) / elapsed_time
    iops = count / elapsed_time
    avg_latency = statistics.mean(latencies) * 1000 if latencies else 0
    
    # P95 Latency calculation
    if len(latencies) >= 20:
        p95_latency = statistics.quantiles(latencies, n=20)[18] * 1000
    else:
        p95_latency = avg_latency

    print(f"\n--- {label} Results ---")
    print(f"Files processed: {count}")
    print(f"Total data:      {total_bytes / (1024 * 1024):.2f} MB")
    print(f"Elapsed time:    {elapsed_time:.4f} s")
    print(f"Throughput:      {mb_per_sec:.2f} MB/s")
    print(f"IOPS:            {iops:.2f}")
    print(f"Avg Latency:     {avg_latency:.4f} ms")
    print(f"P95 Latency:     {p95_latency:.4f} ms")

def main():
    parser = argparse.ArgumentParser(description="Advanced Disk I/O Performance Tester")
    parser.add_argument("--threads", type=int, default=1, help="Number of worker threads (default: 1)")
    parser.add_argument("--n", type=int, default=1, help="Number of files to process (default: 1)")
    parser.add_argument("--size", type=int, default=4096, help="Size of each file in bytes (default: 4096)")
    parser.add_argument("--mode", choices=['write', 'read', 'both'], default='both', help="Test mode (default: both)")
    parser.add_argument("--dir", type=str, help="Directory to use for testing (required for 'read' mode if not using 'both')")
    
    default_drive = "D" if os.name == "nt" else ""
    parser.add_argument("--drive", type=str, default=default_drive, help="Drive/Path to test (default: 'D' on Windows, system default temp on Linux/macOS)")

    args = parser.parse_args()

    if args.threads <= 0 or args.n <= 0 or args.size <= 0:
        print("Error: threads, n, and size must be positive integers.")
        sys.exit(1)

    # Validation for read mode
    if args.mode == 'read' and not args.dir:
        print("Error: For 'read' mode, you must specify a directory using --dir.")
        sys.exit(1)

    print(f"Configuration: Threads={args.threads}, Files={args.n}, Size={args.size} bytes, Mode={args.mode}, Drive={args.drive}")
    if args.dir:
        print(f"Target Directory: {args.dir}")
    else:
        print(f"Target Directory: [Temporary Directory on Drive {args.drive}]")

    # Determine working directory
    if args.mode == 'both' or args.mode == 'write':
        # Use temp dir for write/both to be safe
        if os.name == 'nt':
            drive_letter = args.drive.rstrip(":\\")
            base_dir = Path(f"{drive_letter}:\\")
            if not base_dir.exists():
                print(f"Error: Drive {base_dir} does not exist or is not accessible.")
                sys.exit(1)
            else:
                try:
                    temp_dir_context = tempfile.TemporaryDirectory(dir=base_dir)
                except Exception as e:
                    print(f"Error: Could not create temp directory on {base_dir} ({e}).")
                    sys.exit(1)
        else:
            try:
                temp_dir_context = tempfile.TemporaryDirectory(dir=Path(args.drive) if args.drive else None)
            except Exception as e:
                print(f"Error: Could not create temp directory on {args.drive} ({e}).")
                sys.exit(1)
        working_dir = Path(temp_dir_context.name)
    elif args.mode == 'read':
        working_dir = Path(args.dir)
    else:
        # This case shouldn't be reachable due to validation
        sys.exit(1)
    
    # Pre-generate data to avoid CPU bottleneck during timing
    print("Pre-generating random data buffers to avoid CPU bottleneck...")
    data_low = generate_random_bytes(args.size // 2)
    data_mid = generate_random_bytes(args.size)
    data_high = generate_random_bytes(args.size * 2)

    try:
        write_files = []
        write_latencies = []

        # --- WRITE TEST ---
        if args.mode in ['write', 'both']:
            print(f"\nStarting WRITE test...")
            start_time = time.perf_counter()
            
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = []
                for i in range(args.n):
                    rem = i % 3
                    if rem == 0:
                        data = data_low
                    elif rem == 1:
                        data = data_mid
                    else:
                        data = data_high
                    futures.append(executor.submit(write_task, i, data, working_dir))
                
                for future in as_completed(futures):
                    try:
                        f_path, latency, bytes_written = future.result()
                        write_files.append((f_path, bytes_written))
                        write_latencies.append(latency)
                    except Exception as e:
                        print(f"Error during write: {e}", file=sys.stderr)

            total_bytes_written = sum(bytes_written for _, bytes_written in write_files)
            elapsed_time = time.perf_counter() - start_time
            print_metrics("WRITE", len(write_files), total_bytes_written, elapsed_time, write_latencies)

        # --- READ TEST ---
        if args.mode in ['read', 'both']:
            # If mode is 'both', we use the files we just wrote.
            # If mode is 'read', we use files in the provided --dir.
            files_to_read = []
            if args.mode == 'both':
                files_to_read = [f_path for f_path, _ in write_files]
            else:
                # Read all .bin files in the specified directory
                files_to_read = list(working_dir.glob("*.bin"))
                if not files_to_read:
                    print(f"Error: No .bin files found in {working_dir} for reading.")
                    sys.exit(1)

            print(f"\nStarting READ test ({len(files_to_read)} files, mid-size {args.size} bytes, {args.threads} threads)...")
            read_latencies = []
            total_bytes_read = 0
            start_time = time.perf_counter()
            
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = [executor.submit(read_task, f_path) for f_path in files_to_read]
                for future in as_completed(futures):
                    try:
                        latency, bytes_read = future.result()
                        read_latencies.append(latency)
                        total_bytes_read += bytes_read
                    except Exception as e:
                        print(f"Error during read: {e}", file=sys.stderr)

            elapsed_time = time.perf_counter() - start_time
            print_metrics("READ", len(read_latencies), total_bytes_read, elapsed_time, read_latencies)

    finally:
        # Cleanup temp directory if we created one
        if args.mode in ['write', 'both'] and not args.dir:
            temp_dir_context.cleanup()

if __name__ == "__main__":
    main()