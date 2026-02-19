#!/usr/bin/env python3
"""
SIMPLIFIED MAC PERFORMANCE DIAGNOSTIC
Quick analysis of system resources and Docker container issues.
"""

import subprocess
import os
import sys
from datetime import datetime


def get_basic_system_info():
    """Get basic system information."""
    print("🖥️ SYSTEM INFORMATION")
    print("=" * 50)

    try:
        # CPU and Memory
        result = subprocess.run(
            ["sysctl", "-n", "hw.ncpu"], capture_output=True, text=True
        )
        cpu_cores = result.stdout.strip() if result.returncode == 0 else "Unknown"

        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True
        )
        if result.returncode == 0:
            mem_kb = int(result.stdout.strip())
            mem_gb = mem_kb / (1024 * 1024)
            print(f"💻 CPU Cores: {cpu_cores}")
            print(f"💾 Total RAM: {mem_gb:.1f} GB")
        else:
            print("❌ Could not get memory info")

    except Exception as e:
        print(f"❌ Error getting system info: {e}")

    print()


def check_docker_memory_usage():
    """Check Docker container memory usage."""
    print("🐳 DOCKER MEMORY ANALYSIS")
    print("=" * 50)

    try:
        # Get container memory stats
        result = subprocess.run(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")

            high_memory_containers = []
            total_memory_mb = 0

            print("📊 Container Memory Usage:")

            for i, line in enumerate(lines[1:], 1):  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        name = parts[0]
                        mem_usage = parts[1]
                        mem_percent = parts[2].replace("%", "")

                        # Convert memory usage to MB (approximate)
                        try:
                            if "MiB" in mem_usage:
                                mem_mb = float(mem_usage.replace("MiB", ""))
                            elif "GiB" in mem_usage:
                                mem_mb = float(mem_usage.replace("GiB", "")) * 1024
                            else:
                                # Try to extract number
                                import re

                                numbers = re.findall(r"[\d.]+", mem_usage)
                                mem_mb = float(numbers[0]) if numbers else 0

                            total_memory_mb += mem_mb

                            if mem_percent and float(mem_percent) > 80:
                                high_memory_containers.append(
                                    f"{name} ({mem_percent}% {mem_usage})"
                                )

                            print(
                                f"   {i:2d}. 📦 {name[:25]:25} Mem: {mem_percent:>4}% ({mem_usage})"
                            )

                        except:
                            print(f"   {i:2d}. 📦 {name[:25]:25} Mem: {mem_usage}")

            print(
                f"\n💾 Total Container Memory: {total_memory_mb:.0f} MB ({total_memory_mb / 1024:.1f} GB)"
            )

            if high_memory_containers:
                print(f"\n🚨 HIGH MEMORY USAGE:")
                for container in high_memory_containers:
                    print(f"   🔥 {container}")
            else:
                print(f"\n✅ Memory usage looks normal")

    except Exception as e:
        print(f"❌ Error checking Docker memory: {e}")

    print()


def check_problematic_container_logs():
    """Check logs for containers with known issues."""
    print("📋 PROBLEMATIC CONTAINER LOGS")
    print("=" * 50)

    # Focus on containers that commonly have issues
    problematic_containers = [
        "somastack_postgres",
        "somastack_kafka",
        "somastack_milvus",
    ]

    for container in problematic_containers:
        print(f"🔍 Checking {container} logs...")

        try:
            # Get last 30 lines of logs
            result = subprocess.run(
                ["docker", "logs", "--tail", "30", container],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                logs = result.stdout
                issues_found = []

                # Check for common issues
                if any(
                    keyword.lower() in logs.lower()
                    for keyword in [
                        "out of memory",
                        "oomkilled",
                        "cannot allocate memory",
                        "memory allocation failure",
                        "killed",
                        "fatal",
                        "error",
                        "connection refused",
                        "timeout",
                        "slow query",
                    ]
                ):
                    issues_found.append("Memory/Connection Issues")

                if "restarting" in logs.lower():
                    issues_found.append("Container Restarting")

                if "database is locked" in logs.lower():
                    issues_found.append("Database Lock Issues")

                if issues_found:
                    print(f"   ⚠️  Issues: {', '.join(issues_found)}")

                    # Show last few lines with issues
                    lines = logs.strip().split("\n")
                    for i, line in enumerate(lines[-5:], len(lines) - 4):
                        if any(
                            keyword.lower() in line.lower()
                            for keyword in ["error", "fatal", "killed", "out of memory"]
                        ):
                            print(f"      {i + len(lines) - 4}: {line.strip()}")
                else:
                    print(f"   ✅ No obvious issues in recent logs")

            else:
                print(f"   ❌ Could not get logs for {container}")

        except Exception as e:
            print(f"   ❌ Error checking {container} logs: {str(e)[:50]}")

        print()


def check_docker_daemon_status():
    """Check Docker daemon status."""
    print("🔧 DOCKER DAEMON STATUS")
    print("=" * 50)

    try:
        # Test Docker daemon
        result = subprocess.run(
            ["docker", "version"], capture_output=True, text=True, timeout=5
        )

        if result.returncode == 0:
            print("✅ Docker daemon is responsive")

            # Get system info
            info_result = subprocess.run(
                ["docker", "system", "info"], capture_output=True, text=True, timeout=5
            )

            if info_result.returncode == 0:
                info = info_result.stdout

                if "WARNING" in info:
                    print("⚠️  Docker daemon has warnings")

                # Check for memory info
                if "Total Memory" in info:
                    print("📊 Docker memory info available")

        else:
            print("❌ Docker daemon not responding to version command")

    except Exception as e:
        print(f"❌ Error checking Docker daemon: {str(e)[:50]}")

    print()


def check_system_resources():
    """Check overall system resource usage."""
    print("📈 SYSTEM RESOURCE USAGE")
    print("=" * 50)

    try:
        # Get load average
        with open("/proc/loadavg", "r") as f:
            load_avg = f.read().strip().split()
            if len(load_avg) >= 3:
                print(
                    f"📊 Load Average (1/5/15 min): {load_avg[0]}, {load_avg[1]}, {load_avg[2]}"
                )

                # Get CPU count
                with open("/proc/cpuinfo", "r") as cpuinfo:
                    cpu_count = cpuinfo.count("processor")
                    if load_avg[0] > cpu_count:
                        print("🚨 CRITICAL: System overloaded!")
                    elif float(load_avg[0]) > cpu_count * 0.8:
                        print("⚠️  WARNING: High system load!")
                    else:
                        print("✅ System load is normal")

        # Get memory usage
        with open("/proc/meminfo", "r") as meminfo:
            for line in meminfo:
                if line.startswith("MemTotal:"):
                    total_kb = int(line.split()[1])
                    total_gb = total_kb / (1024 * 1024)
                elif line.startswith("MemAvailable:"):
                    available_kb = int(line.split()[1])
                    available_gb = available_kb / (1024 * 1024)
                    used_percent = ((total_kb - available_kb) / total_kb) * 100

                    if used_percent > 90:
                        print("🚨 CRITICAL: Very high memory usage!")
                    elif used_percent > 80:
                        print("⚠️  WARNING: High memory usage!")
                    elif used_percent > 70:
                        print("🟡 CAUTION: Moderate memory usage!")
                    else:
                        print("✅ Memory usage is acceptable")

                    print(
                        f"💾 Memory: {available_gb:.1f} GB free ({100 - used_percent:.1f}% used)"
                    )
                    break

    except Exception as e:
        print(f"❌ Error checking system resources: {str(e)[:50]}")

    print()


def provide_tuning_recommendations():
    """Provide specific tuning recommendations."""
    print("💡 PERFORMANCE TUNING RECOMMENDATIONS")
    print("=" * 50)

    print("🐳 DOCKER OPTIMIZATION:")
    print("   1. Set memory limits for containers:")
    print("      docker run --memory=2g [image]")
    print("      # Or in docker-compose.yml:")
    print("      deploy:")
    print("        resources:")
    print("          limits:")
    print("            memory: 2G")
    print("")
    print("   2. Monitor container resource usage:")
    print("      docker stats --no-stream")
    print("      watch -n 2 'docker stats --no-stream'")
    print("")
    print("   3. Clean up Docker resources:")
    print("      docker system prune -f")
    print("      docker volume prune -f")
    print("")
    print("   4. Restart Docker daemon if needed:")
    print("      sudo killall Docker && open -a Docker")
    print("")
    print("   5. Optimize Docker Desktop settings:")
    print("      - Reduce memory allocation to Docker Desktop")
    print("      - Adjust CPU limits in Docker Desktop")
    print("      - Use fewer simultaneous containers")
    print("")

    print("🖥️ MAC SYSTEM OPTIMIZATION:")
    print("   1. Check Activity Monitor (⌘⌥)")
    print("   2. Close unnecessary applications")
    print("   3. Clear browser caches and tabs")
    print("   4. Check Spotlight indexing (may impact performance)")
    print("   5. Restart system if needed")
    print("")

    print("📊 MEMORY TROUBLESHOOTING:")
    print("   1. Clear system caches:")
    print("      sudo purge")
    print("      sudo rm -rf /tmp/*")
    print("")
    print("   2. Check for memory leaks:")
    print("      leaks -atExit -no-copy -all -- python /path/to/app")
    print("      instrument code with memory_profiler")
    print("")
    print("   3. Increase swap file if needed:")
    print("      sudo fallocate -l 2G /swapfile")
    print("      sudo chmod 600 /swapfile")
    print("      sudo mkswap /swapfile")
    print("      sudo swapon /swapfile")
    print("")


def main():
    """Main diagnostic function."""
    print("🔍 MAC PERFORMANCE & DOCKER DIAGNOSTIC")
    print("🚀 Checking memory, communication, and performance issues")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    # Run all checks
    get_basic_system_info()
    check_docker_memory_usage()
    check_problematic_container_logs()
    check_docker_daemon_status()
    check_system_resources()

    # Provide recommendations
    provide_tuning_recommendations()

    print("\n" + "=" * 80)
    print("🏆 DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print("Review the analysis above for specific issues and optimizations.")


if __name__ == "__main__":
    main()
