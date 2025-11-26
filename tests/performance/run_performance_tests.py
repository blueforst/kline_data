#!/usr/bin/env python3
"""
Performance Test Runner

Example script demonstrating how to run and analyze K-line data system performance tests.
"""

import sys
import os
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime

def run_performance_tests(test_type="all", output_dir=None):
    """
    Run performance tests and generate reports

    Args:
        test_type: Type of tests to run ('all', 'client', 'memory', 'storage', 'api', 'indicators')
        output_dir: Directory to save reports
    """

    # Set up output directory
    if output_dir is None:
        output_dir = Path("performance_results")
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(exist_ok=True)

    print(f"🚀 Starting K-line Data System Performance Tests")
    print(f"📊 Test Type: {test_type}")
    print(f"📁 Output Directory: {output_dir}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Define test configurations
    test_configs = {
        "all": {
            "path": "tests/performance/",
            "description": "All Performance Tests"
        },
        "client": {
            "path": "tests/performance/test_client_performance.py",
            "description": "KlineClient Performance Tests"
        },
        "memory": {
            "path": "tests/performance/test_chunked_data_feed_performance.py",
            "description": "Memory Efficiency Tests"
        },
        "storage": {
            "path": "tests/performance/test_storage_performance.py",
            "description": "Storage I/O Performance Tests"
        },
        "api": {
            "path": "tests/performance/test_api_performance.py",
            "description": "API Service Performance Tests"
        },
        "indicators": {
            "path": "tests/performance/test_indicators_performance.py",
            "description": "Technical Indicators Performance Tests"
        },
        "config": {
            "path": "tests/performance/test_config_performance.py",
            "description": "Configuration Performance Tests"
        },
        "download": {
            "path": "tests/performance/test_download_resample_performance.py",
            "description": "Download and Resampling Performance Tests"
        },
        "regression": {
            "path": "tests/performance/test_performance_regression.py",
            "description": "Performance Regression Tests"
        },
        "reporting": {
            "path": "tests/performance/test_performance_reporting.py",
            "description": "Performance Analysis and Reporting"
        }
    }

    # Validate test type
    if test_type not in test_configs:
        print(f"❌ Unknown test type: {test_type}")
        print(f"Available types: {', '.join(test_configs.keys())}")
        return 1

    config = test_configs[test_type]

    # Prepare pytest command
    pytest_cmd = [
        "python", "-m", "pytest",
        config["path"],
        "-v",
        "--benchmark-only",
        "--benchmark-sort=mean",
        "--benchmark-json", str(output_dir / "benchmark_results.json"),
        "--benchmark-html", str(output_dir / "benchmark_report.html"),
        "--benchmark-min-rounds=3"
    ]

    # Add specific markers if needed
    if test_type in ["all"]:
        pytest_cmd.extend(["-m", "performance or benchmark"])

    print(f"🔧 Running: {' '.join(pytest_cmd)}")
    print(f"📝 Description: {config['description']}")
    print()

    # Run the tests
    try:
        start_time = time.time()
        result = subprocess.run(pytest_cmd, capture_output=True, text=True, cwd=Path.cwd())
        end_time = time.time()

        # Save output
        with open(output_dir / "test_output.log", "w") as f:
            f.write(f"=== Test Output ===\n")
            f.write(f"Command: {' '.join(pytest_cmd)}\n")
            f.write(f"Exit Code: {result.returncode}\n")
            f.write(f"Duration: {end_time - start_time:.2f} seconds\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
            f.write("=== STDOUT ===\n")
            f.write(result.stdout)
            f.write("\n=== STDERR ===\n")
            f.write(result.stderr)

        if result.returncode == 0:
            print("✅ Performance tests completed successfully!")
        else:
            print("❌ Performance tests failed!")
            print(f"Exit code: {result.returncode}")
            print("Check the log file for details:", output_dir / "test_output.log")

        # Print summary
        duration = end_time - start_time
        print(f"\n📊 Test Summary:")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📁 Results saved to: {output_dir}")
        print(f"📈 Benchmark report: {output_dir / 'benchmark_report.html'}")

        # Analyze results if available
        benchmark_file = output_dir / "benchmark_results.json"
        if benchmark_file.exists():
            analyze_benchmark_results(benchmark_file, output_dir)

        return result.returncode

    except FileNotFoundError:
        print("❌ pytest not found. Please install pytest and pytest-benchmark:")
        print("pip install pytest pytest-benchmark psutil matplotlib seaborn")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

def analyze_benchmark_results(results_file, output_dir):
    """Analyze benchmark results and generate summary"""

    try:
        with open(results_file, 'r') as f:
            results = json.load(f)

        if not results.get("benchmarks"):
            print("⚠️  No benchmark results found")
            return

        benchmarks = results["benchmarks"]

        print("\n📈 Benchmark Analysis:")

        # Analyze by test
        test_stats = {}
        for benchmark in benchmarks:
            test_name = benchmark.get("name", "unknown")
            if test_name not in test_stats:
                test_stats[test_name] = {
                    "min": float('inf'),
                    "max": 0,
                    "mean": 0,
                    "count": 0,
                    "total": 0
                }

            stats = test_stats[test_name]
            stats["min"] = min(stats["min"], benchmark["min"])
            stats["max"] = max(stats["max"], benchmark["max"])
            stats["mean"] = stats["total"] / (stats["count"] + 1)
            stats["total"] += benchmark["mean"]
            stats["count"] += 1

        # Display statistics
        for test_name, stats in sorted(test_stats.items()):
            print(f"  📊 {test_name}:")
            print(f"    Min: {stats['min']:.6f}s")
            print(f"    Max: {stats['max']:.6f}s")
            print(f"    Mean: {stats['mean']:.6f}s")
            print(f"    Samples: {stats['count']}")

        # Generate summary report
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(test_stats),
            "test_statistics": test_stats
        }

        with open(output_dir / "summary_report.json", "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n📄 Summary report saved to: {output_dir / 'summary_report.json'}")

    except Exception as e:
        print(f"⚠️  Error analyzing results: {e}")

def show_help():
    """Show help information"""
    print("K-line Data System Performance Test Runner")
    print()
    print("Usage:")
    print("  python run_performance_tests.py [test_type] [output_dir]")
    print()
    print("Test Types:")
    for test_type, config in {
        "all": "Run all performance tests",
        "client": "KlineClient performance tests",
        "memory": "Memory efficiency tests",
        "storage": "Storage I/O performance tests",
        "api": "API service performance tests",
        "indicators": "Technical indicators performance tests",
        "config": "Configuration performance tests",
        "download": "Download and resampling performance tests",
        "regression": "Performance regression tests",
        "reporting": "Performance analysis and reporting"
    }.items():
        print(f"  {test_type:<12} {config}")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="K-line Data System Performance Test Runner")
    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        help="Type of performance tests to run (default: all)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Directory to save test results (default: ./performance_results)"
    )
    parser.add_argument(
        "--help", "-h",
        action="store_true",
        help="Show this help message"
    )

    args = parser.parse_args()

    if args.help:
        show_help()
        return 0

    return run_performance_tests(args.test_type, args.output_dir)

if __name__ == "__main__":
    sys.exit(main())