#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Benchmark script for Epic Games Claimer.

Measures:
- Wall-clock runtime
- CPU usage (%) during run
- Memory (RSS) usage over time and peak
- I/O read/write bytes
- Logs results to logs/benchmark-YYYYMMDD-HHMMSS.json and prints summary.
"""
import json
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

try:
    import psutil
except ImportError:
    print("psutil não está instalado. Execute: pip install psutil")
    sys.exit(1)

ROOT = Path(__file__).parent.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

PYTHON_EXE = sys.executable
MAIN_PATH = ROOT / "main.py"
MAIN_ARGS = ["--schedule"]  # keep process alive to measure sustained CPU

# Default low-CPU settings for benchmark (overridable via env)
DEFAULT_LOW_CPU_MODE = os.getenv('LOW_CPU_MODE', 'true')
DEFAULT_LOW_CPU_SLEEP_MS = os.getenv('LOW_CPU_SLEEP_MS', '1000')
SAMPLE_INTERVAL = float(os.getenv('BENCH_SAMPLE_INTERVAL', '0.5'))
MAX_SECONDS = float(os.getenv('BENCH_MAX_SECONDS', '120'))


def run_and_measure(cmd, max_seconds: float = MAX_SECONDS):
    start_time = time.time()
    proc = psutil.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p = psutil.Process(proc.pid)

    cpu_samples = []
    mem_samples = []
    io_samples = []

    # prime CPU percent for the process
    try:
        p.cpu_percent(interval=None)
    except Exception:
        pass

    while True:
        if proc.poll() is not None:
            break
        # exit if exceeded max_seconds
        if (time.time() - start_time) > max_seconds:
            try:
                proc.terminate()
            except Exception:
                pass
            break
        try:
            cpu = p.cpu_percent(interval=SAMPLE_INTERVAL)
            mem = p.memory_info().rss
            io = p.io_counters() if hasattr(p, 'io_counters') else None
            read_bytes = io.read_bytes if io else 0
            write_bytes = io.write_bytes if io else 0
        except psutil.Error:
            cpu = 0.0
            mem = 0
            read_bytes = 0
            write_bytes = 0

        cpu_samples.append(cpu)
        mem_samples.append(mem)
        io_samples.append((read_bytes, write_bytes))

    end_time = time.time()
    out, err = proc.communicate()

    duration = end_time - start_time
    peak_mem = max(mem_samples) if mem_samples else 0
    avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0

    # last IO sample
    total_read = io_samples[-1][0] if io_samples else 0
    total_write = io_samples[-1][1] if io_samples else 0

    return {
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "duration_seconds": round(duration, 3),
        "cpu_avg_percent_process": round(avg_cpu, 2),
        "memory_peak_bytes": peak_mem,
        "memory_peak_mb": round(peak_mem / (1024 * 1024), 2),
        "io_read_bytes": total_read,
        "io_write_bytes": total_write,
        "samples": {
            "cpu_percent_process": cpu_samples,
            "rss_bytes": mem_samples,
        },
        "stdout_head": out.decode(errors="ignore").splitlines()[:50],
        "stderr_head": err.decode(errors="ignore").splitlines()[:50],
    }


def main():
    if not MAIN_PATH.exists():
        print(f"Arquivo não encontrado: {MAIN_PATH}")
        sys.exit(1)

    cmd = [PYTHON_EXE, str(MAIN_PATH)] + MAIN_ARGS
    # Allow LOW_CPU_MODE during benchmark to simulate reduced load
    os.environ.setdefault('LOW_CPU_MODE', DEFAULT_LOW_CPU_MODE)
    os.environ.setdefault('LOW_CPU_SLEEP_MS', DEFAULT_LOW_CPU_SLEEP_MS)
    print(
        f"Iniciando benchmark: python main.py --schedule "
        f"(timeout {int(MAX_SECONDS)}s, LOW_CPU_MODE={os.environ['LOW_CPU_MODE']}, "
        f"LOW_CPU_SLEEP_MS={os.environ['LOW_CPU_SLEEP_MS']}, sample={SAMPLE_INTERVAL}s)"
    )
    result = run_and_measure(cmd, max_seconds=MAX_SECONDS)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = LOG_DIR / f"benchmark-{timestamp}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\nResumo do Benchmark:")
    print(f"  Duração:         {result['duration_seconds']} s")
    cpu_value = result.get('cpu_avg_percent_process', result.get('cpu_avg_percent', 0))
    print(f"  CPU média:       {cpu_value} %")
    print(f"  Memória pico:    {result['memory_peak_mb']} MB")
    print(f"  IO leitura:      {result['io_read_bytes']} bytes")
    print(f"  IO escrita:      {result['io_write_bytes']} bytes")
    print(f"  Exit code:       {result['exit_code']}")
    print(f"  Log:             {out_file}")

    # Simple recommendations
    if result['memory_peak_mb'] > 500:
        print("  ⚠️ Memória alta: considere reduzir payloads ou dividir etapas.")
    if cpu_value > 75:
        print("  ⚠️ CPU alta: considere aumentar timeouts ou usar sleep entre requests.")


if __name__ == "__main__":
    main()
