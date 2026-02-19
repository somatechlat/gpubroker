#!/usr/bin/env python3
"""
MAC PERFORMANCE DIAGNOSTIC TOOL
Comprehensive system analysis for Mac performance issues with Docker containers.
"""

import subprocess
import psutil
import os
import time
from datetime import datetime


def get_system_info():
    """Get comprehensive system information."""
    print("🖥️ MAC SYSTEM INFORMATION")
    print("=" * 60)

    # Basic system info
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # CPU Info
    try:
        cpu_info = psutil.cpu_info()
        print(f"💻 CPU: {cpu_info.brand}")
        print(
            f"🔧 Cores: {psutil.cpu_count(logical=True)} logical ({psutil.cpu_count(logical=False)} physical)"
        )
        if hasattr(cpu_info, "current_freq") and cpu_info.current_freq:
            print(f"⚡ Current Frequency: {cpu_info.current_freq:.0f} MHz")
        if hasattr(cpu_info, "max_freq") and cpu_info.max_freq:
            print(f"🎯 Max Frequency: {cpu_info.max_freq:.0f} MHz")
    except Exception as e:
        print(
            f"💻 CPU: {psutil.cpu_count(logical=True)} cores (error getting details: {e})"
        )
    print()

    # Memory Info
    memory = psutil.virtual_memory()
    print(f"💾 Total RAM: {memory.total / (1024**3):.1f} GB")
    print(
        f"📊 Available RAM: {memory.available / (1024**3):.1f} GB ({memory.available / memory.total * 100:.1f}%)"
    )
    print(f"📈 Used RAM: {memory.used / (1024**3):.1f} GB ({memory.percent}%)")
    print(f"🔄 Swap: {memory.total / (1024**3):.1f} GB")
    print()

    # Disk Info
    disk = psutil.disk_usage("/")
    print(f"💿 Total Disk: {disk.total / (1024**3):.1f} GB")
    print(
        f"📊 Available Disk: {disk.free / (1024**3):.1f} GB ({disk.free / disk.total * 100:.1f}%)"
    )
    print(f"📈 Used Disk: {disk.used / (1024**3):.1f} GB ({disk.percent}%)")
    print()

    return {
        "cpu_cores": psutil.cpu_count(logical=True),
        "memory_total": memory.total,
        "memory_available": memory.available,
        "memory_percent": memory.percent,
        "disk_total": disk.total,
        "disk_free": disk.free,
    }


def check_docker_resources():
    """Check Docker-specific resource usage."""
    print("🐳 DOCKER RESOURCE ANALYSIS")
    print("=" * 50)

    try:
        # Docker system info
        docker_info = subprocess.run(
            ["docker", "system", "df"], capture_output=True, text=True, timeout=10
        )

        if docker_info.returncode == 0:
            print("💿 Docker Disk Usage:")
            for line in docker_info.stdout.strip().split("\n")[1:]:  # Skip header
                if line.strip():
                    print(f"   {line}")

        # Docker container stats
        print("\n📊 Container Resource Analysis:")

        # Get container stats summary
        stats_result = subprocess.run(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if stats_result.returncode == 0:
            lines = stats_result.stdout.strip().split("\n")

            total_memory = 0
            high_cpu_containers = []

            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        name = parts[0]
                        cpu = float(parts[1].replace("%", ""))
                        mem_usage = parts[2]
                        mem_percent = parts[3].replace("%", "")

        try:
            # Convert memory usage to bytes (strip GiB/MB/etc)
            mem_bytes = 0
            if mem_usage:
                if 'GiB' in mem_usage:
                    mem_bytes = float(mem_usage.replace('GiB', '')) * (1024**3)
                elif 'MiB' in mem_usage:
                    mem_bytes = float(mem_usage.replace('MiB', '')) * (1024**2)
                elif 'KiB' in mem_usage:
                    mem_bytes = float(mem_usage.replace('KiB', '')) * 1024
                else:
                    # Try to parse numeric value
                    import re
                    numeric = re.findall(r'[\d.]+', mem_usage)
                    if numeric:
                        mem_bytes = float(numeric[0]) * 1024  # Assume MB
                    else:
                        mem_bytes = 0

                            total_memory += mem_bytes

                            if cpu > 80:
                                high_cpu_containers.append(f"{name} ({cpu}%)")

                        except:
                            pass

                        print(
                            f"   📦 {name[:20]:20} CPU: {cpu:>5}% Mem: {mem_percent:>4}%"
                        )

            if total_memory > 0:
                total_gb = total_memory / (1024**3)
                print(f"\n💾 Total Container Memory: {total_gb:.2f} GB")

            if high_cpu_containers:
                print(f"\n⚠️  HIGH CPU USAGE DETECTED:")
                for container in high_cpu_containers:
                    print(f"   🔥 {container}")

    except Exception as e:
        print(f"❌ Error checking Docker resources: {str(e)}")


def check_system_pressure():
    """Check system pressure indicators."""
    print("\n🔥 SYSTEM PRESSURE INDICATORS")
    print("=" * 50)

    # Load average
    try:
        load_avg = os.getloadavg()
        print(
            f"📈 Load Average (1/5/15 min): {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}"
        )

        cpu_cores = psutil.cpu_count()
        if load_avg and len(load_avg) >= 1:
            if load_avg[0] > cpu_cores * 2:
                print("🚨 CRITICAL: System severely overloaded!")
            elif load_avg[0] > cpu_cores:
                print("⚠️  WARNING: High system load detected")
            elif load_avg[0] > cpu_cores * 0.7:
                print("🟡 CAUTION: Moderate system load")
            else:
                print("✅ System load is normal")
        else:
            print("📊 Could not determine load average")
        print()

    except Exception as e:
        print(f"❌ Error checking load average: {str(e)}")

    # Memory pressure
    try:
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            print("🚨 CRITICAL: Very high memory usage!")
        elif memory.percent > 80:
            print("⚠️  WARNING: High memory usage")
        elif memory.percent > 70:
            print("🟡 CAUTION: Moderate memory usage")
        else:
            print("✅ Memory usage is normal")
        print()

    except Exception as e:
        print(f"❌ Error checking memory pressure: {str(e)}")


def check_docker_logs():
    """Check Docker logs for performance issues."""
    print("\n📋 DOCKER LOGS ANALYSIS")
    print("=" * 50)

    problematic_containers = [
        "somastack_postgres",
        "somastack_kafka",
        "somastack_milvus",
        "somastack_saas",
    ]

    for container in problematic_containers:
        try:
            print(f"🔍 Checking logs for {container}...")

            # Get recent logs (last 20 lines)
            log_result = subprocess.run(
                ["docker", "logs", "--tail", "20", container],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if log_result.returncode == 0:
                logs = log_result.stdout.strip()

                # Look for performance issues
                issues = []
                if "error" in logs.lower():
                    issues.append("Errors")
                if "timeout" in logs.lower():
                    issues.append("Timeouts")
                if "out of memory" in logs.lower():
                    issues.append("Memory Issues")
                if "connection refused" in logs.lower():
                    issues.append("Connection Issues")
                if "slow" in logs.lower():
                    issues.append("Performance Issues")
                if "killed" in logs.lower():
                    issues.append("Process Killed")

                if issues:
                    print(f"   ⚠️  Issues found: {', '.join(issues)}")
                else:
                    print(f"   ✅ No obvious issues in recent logs")

            else:
                print(f"   ❌ Could not retrieve logs for {container}")

        except Exception as e:
            print(f"   ❌ Error checking {container} logs: {str(e)[:50]}")

        print()


def check_communication_issues():
    """Check for common communication issues."""
    print("🔗 COMMUNICATION ISSUES CHECK")
    print("=" * 50)

    # Check port conflicts
    print("🔍 Checking for port conflicts...")

    try:
        # Get all used ports
        result = subprocess.run(
            ["lsof", "-i", "-P", "-n", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            port_counts = {}
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 9:
                        port = parts[8]
                        if port in port_counts:
                            port_counts[port] += 1
                        else:
                            port_counts[port] = 1

            conflicts = [port for port, count in port_counts.items() if count > 1]

            if conflicts:
                print(f"⚠️  Port conflicts detected: {conflicts}")
            else:
                print("✅ No obvious port conflicts")

    except Exception as e:
        print(f"❌ Error checking port conflicts: {str(e)[:50]}")

    print()

    # Check Docker daemon
    try:
        docker_result = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=10
        )

        if docker_result.returncode == 0:
            info = docker_result.stdout

            # Check for common issues
            if "WARNING" in info:
                print("⚠️  Docker daemon warnings detected")

            if "No swap limit" in info and "Memory" in info:
                print("🟡 Consider Docker memory limits")

            print("✅ Docker daemon is responsive")

    except Exception as e:
        print(f"❌ Error checking Docker daemon: {str(e)[:50]}")


def provide_recommendations(system_info):
    """Provide performance recommendations based on system state."""
    print("\n💡 PERFORMANCE RECOMMENDATIONS")
    print("=" * 50)

    memory_pressure = system_info["memory_percent"]
    available_memory = system_info["memory_available"]
    cpu_cores = system_info["cpu_cores"]

    # Memory recommendations
    if memory_pressure > 85:
        print("🚨 MEMORY CRITICAL:")
        print("   1. Close unnecessary applications")
        print("   2. Clear browser caches")
        print("   3. Restart memory-intensive containers")
        print("   4. Consider increasing swap file")
    elif memory_pressure > 70:
        print("⚠️  MEMORY WARNING:")
        print("   1. Monitor memory-intensive containers")
        print("   2. Check for memory leaks")
        print("   3. Optimize Docker memory limits")
    else:
        print("✅ Memory usage is acceptable")

    print()

    # Container-specific recommendations
    print("🐳 DOCKER OPTIMIZATION:")

    if available_memory < 4 * 1024**3:  # Less than 4GB available
        print("🟡 LOW MEMORY DETECTED:")
        print("   1. Set memory limits on containers")
        print("   2. Stop unused containers")
        print("   3. Use --memory parameter when appropriate")

    print("   4. Consider Docker Compose resource limits")
    print("   5. Monitor with 'docker stats' regularly")

    print()

    # System recommendations
    print("🖥️ MAC SYSTEM OPTIMIZATION:")
    print("   1. Check Activity Monitor for CPU/memory usage")
    print("   2. Close unnecessary browser tabs and applications")
    print("   3. Restart Docker daemon: 'sudo killall Docker && open -a Docker'")
    print("   4. Check for macOS updates")
    print("   5. Consider increasing virtual memory if needed")

    print()
    print("🔧 TROUBLESHOOTING COMMANDS:")
    print("   1. Monitor in real-time: watch -n 2 'docker stats --no-stream'")
    print("   2. Check container logs: docker logs -f [container_name]")
    print("   3. Restart specific container: docker restart [container_name]")
    print("   4. Clean up unused resources: docker system prune -f")
    print("   5. Check disk space: df -h")


def main():
    """Main diagnostic function."""
    print("🔍 MAC PERFORMANCE & DOCKER DIAGNOSTIC TOOL")
    print("🚀 Analyzing system for memory, communication, and performance issues")
    print("=" * 80)

    # Gather system information
    system_info = get_system_info()

    # Check Docker resources
    check_docker_resources()

    # Check system pressure
    check_system_pressure()

    # Check Docker logs for issues
    check_docker_logs()

    # Check communication issues
    check_communication_issues()

    # Provide recommendations
    provide_recommendations(system_info)

    print("\n" + "=" * 80)
    print("🏆 DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print("Review the analysis above for specific issues and recommendations.")


if __name__ == "__main__":
    main()
