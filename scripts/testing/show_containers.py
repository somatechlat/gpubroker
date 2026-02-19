#!/usr/bin/env python3
"""
Container Information Display
Parse and display running container information cleanly.
"""

import subprocess
import json


def get_containers():
    """Get running containers using docker ps."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"Error running docker ps: {result.stderr}")
            return []
    except Exception as e:
        print(f"Error: {str(e)}")
        return []


def main():
    """Display container information."""
    print("🐳 RUNNING DOCKER CONTAINERS")
    print("=" * 80)

    containers = get_containers()

    if not containers:
        print("No containers found")
        return

    print(f"📦 Total Running Containers: {len(containers)}")
    print()

    # Group containers by type
    databases = []
    apps = []
    infrastructure = []

    for container in containers:
        name = container.get("Names", "Unknown")
        image = container.get("Image", "Unknown")
        status = container.get("Status", "Unknown")
        ports = container.get("Ports", "")

        container_info = {
            "name": name,
            "image": image,
            "status": status,
            "ports": ports,
        }

        # Categorize containers
        if any(
            keyword in image.lower()
            for keyword in ["postgres", "redis", "kafka", "etcd", "minio", "clickhouse"]
        ):
            databases.append(container_info)
        elif any(
            keyword in name.lower()
            for keyword in ["soma", "vault", "agent-zero", "lago", "keycloak"]
        ):
            infrastructure.append(container_info)
        else:
            apps.append(container_info)

    # Display by category
    if databases:
        print("💾 DATABASE CONTAINERS:")
        for db in databases:
            print(f"   📊 {db['name']:25} - {db['image']:30} - {db['status']}")
            if db["ports"]:
                print(f"      🔌 Ports: {db['ports'][:60]}...")
        print()

    if infrastructure:
        print("🏗️ INFRASTRUCTURE CONTAINERS:")
        for inf in infrastructure:
            print(f"   🔧 {inf['name']:25} - {inf['image']:30} - {inf['status']}")
            if inf["ports"]:
                print(f"      🔌 Ports: {inf['ports'][:60]}...")
        print()

    if apps:
        print("📱 APPLICATION CONTAINERS:")
        for app in apps:
            print(f"   🚀 {app['name']:25} - {app['image']:30} - {app['status']}")
            if app["ports"]:
                print(f"      🔌 Ports: {app['ports'][:60]}...")
        print()

    # Summary
    print("🔗 PORT MAPPING SUMMARY:")
    port_map = {}

    for container in containers:
        ports = container.get("Ports", "")
        if ports and "->" in ports:
            # Extract port mappings
            for mapping in ports.split(","):
                if "->" in mapping:
                    host_part = mapping.split("->")[-1].strip()
                    if ":" in host_part:
                        host_port = host_part.split(":")[0]
                        port_map[host_port] = container.get("Names", "Unknown")

    if port_map:
        print("   🌐 Host Port -> Container:")
        for port, container in sorted(port_map.items()):
            print(f"      {port:10} -> {container}")

    print()
    print("📊 SYSTEM STATUS:")
    print(
        f"   🟢 Healthy Services: {len([c for c in containers if 'Up' in c.get('Status', '')])}"
    )
    print(f"   🔌 Total Port Mappings: {len(port_map)}")
    print(f"   💾 Database Services: {len(databases)}")
    print(f"   🏗️ Infrastructure Services: {len(infrastructure)}")

    return containers


if __name__ == "__main__":
    main()
