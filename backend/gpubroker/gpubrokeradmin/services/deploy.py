"""
GPUBROKER POD Deployment Service

AWS ECS Fargate deployment for GPUBROKER PODs.
"""

import hashlib
import logging
import os
from typing import Any

logger = logging.getLogger("gpubroker.deploy")

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
ECS_CLUSTER = os.getenv("ECS_CLUSTER", "gpubroker-pods")
ECS_TASK_DEFINITION = os.getenv("ECS_TASK_DEFINITION", "gpubroker-agent-pod")
SUBNETS = os.getenv(
    "ECS_SUBNETS", "subnet-04cc7be08489369a0,subnet-01aa30d4017fc910b"
).split(",")
SECURITY_GROUP = os.getenv("ECS_SECURITY_GROUP", "sg-0661f12cee535a607")
CONTAINER_NAME = "agent-zero"


def _get_boto3_client(service: str):
    """Get boto3 client with error handling."""
    try:
        import boto3

        return boto3.client(service, region_name=AWS_REGION)
    except ImportError:
        logger.warning("boto3 not installed, using mock mode")
        return None
    except Exception as e:
        logger.error(f"Failed to create boto3 client: {e}")
        return None


class DeployService:
    """
    Service for deploying GPUBROKER PODs on AWS ECS Fargate.
    """

    @staticmethod
    def hash_key(api_key: str) -> str:
        """Hash API key for secure storage in pod."""
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]

    @staticmethod
    def deploy_pod(pod_id: str, email: str, plan: str, api_key: str) -> dict[str, Any]:
        """
        Deploy a new GPUBROKER POD on ECS Fargate.

        Args:
            pod_id: Unique pod identifier
            email: Customer email
            plan: Subscription plan
            api_key: API key for the pod

        Returns:
            Dict with deployment result
        """
        ecs = _get_boto3_client("ecs")

        if not ecs:
            # Mock mode for development
            logger.info(f"[Deploy] Mock deployment for pod {pod_id}")
            return {
                "success": True,
                "pod_id": pod_id,
                "task_arn": f"arn:aws:ecs:{AWS_REGION}:mock:task/{pod_id}",
                "pod_url": f"https://{pod_id}.gpubroker.site",
                "status": "provisioning",
            }

        try:
            # Environment variables for the pod
            environment = [
                {"name": "POD_ID", "value": pod_id},
                {"name": "USER_EMAIL", "value": email},
                {"name": "PLAN", "value": plan},
                {"name": "API_KEY_HASH", "value": DeployService.hash_key(api_key)},
            ]

            response = ecs.run_task(
                cluster=ECS_CLUSTER,
                taskDefinition=ECS_TASK_DEFINITION,
                launchType="FARGATE",
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": SUBNETS,
                        "securityGroups": [SECURITY_GROUP],
                        "assignPublicIp": "ENABLED",
                    }
                },
                overrides={
                    "containerOverrides": [
                        {"name": CONTAINER_NAME, "environment": environment}
                    ]
                },
                tags=[
                    {"key": "pod_id", "value": pod_id},
                    {"key": "email", "value": email},
                    {"key": "plan", "value": plan},
                ],
            )

            if response.get("tasks"):
                task = response["tasks"][0]
                logger.info(f"[Deploy] Pod {pod_id} deployed: {task['taskArn']}")
                return {
                    "success": True,
                    "pod_id": pod_id,
                    "task_arn": task["taskArn"],
                    "pod_url": f"https://{pod_id}.gpubroker.site",
                    "status": "provisioning",
                }
            logger.error(f"[Deploy] No task started for pod {pod_id}")
            return {
                "success": False,
                "error": "No task started",
                "failures": response.get("failures", []),
            }

        except Exception as e:
            logger.error(f"[Deploy] Error deploying pod {pod_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed",
            }

    @staticmethod
    def get_pod_status(pod_id: str) -> dict[str, Any]:
        """
        Get the status of a GPUBROKER POD.

        Args:
            pod_id: Pod identifier

        Returns:
            Dict with pod status
        """
        ecs = _get_boto3_client("ecs")

        if not ecs:
            # Mock mode
            return {
                "pod_id": pod_id,
                "status": "running",
                "public_ip": "10.0.0.1",
                "pod_url": f"https://{pod_id}.gpubroker.site",
            }

        try:
            # List tasks with pod_id tag
            response = ecs.list_tasks(cluster=ECS_CLUSTER, desiredStatus="RUNNING")

            if response.get("taskArns"):
                describe = ecs.describe_tasks(
                    cluster=ECS_CLUSTER, tasks=response["taskArns"]
                )

                for task in describe.get("tasks", []):
                    for tag in task.get("tags", []):
                        if tag["key"] == "pod_id" and tag["value"] == pod_id:
                            # Get public IP from network interface
                            public_ip = None
                            for att in task.get("attachments", []):
                                for detail in att.get("details", []):
                                    if detail["name"] == "networkInterfaceId":
                                        ec2 = _get_boto3_client("ec2")
                                        if ec2:
                                            eni = ec2.describe_network_interfaces(
                                                NetworkInterfaceIds=[detail["value"]]
                                            )
                                            if eni.get("NetworkInterfaces"):
                                                public_ip = (
                                                    eni["NetworkInterfaces"][0]
                                                    .get("Association", {})
                                                    .get("PublicIp")
                                                )

                            return {
                                "pod_id": pod_id,
                                "status": (
                                    "running"
                                    if task["lastStatus"] == "RUNNING"
                                    else "provisioning"
                                ),
                                "public_ip": public_ip,
                                "pod_url": f"https://{pod_id}.gpubroker.site",
                            }

            return {
                "pod_id": pod_id,
                "status": "pending",
                "public_ip": None,
                "pod_url": f"https://{pod_id}.gpubroker.site",
            }

        except Exception as e:
            logger.error(f"[Deploy] Error getting pod status: {e}")
            return {
                "pod_id": pod_id,
                "status": "error",
                "error": str(e),
            }

    @staticmethod
    def stop_pod(pod_id: str) -> dict[str, Any]:
        """
        Stop a running GPUBROKER POD.

        Args:
            pod_id: Pod identifier

        Returns:
            Dict with result
        """
        ecs = _get_boto3_client("ecs")

        if not ecs:
            return {"success": True, "message": f"Pod {pod_id} detenido (mock)"}

        try:
            response = ecs.list_tasks(cluster=ECS_CLUSTER)

            for task_arn in response.get("taskArns", []):
                describe = ecs.describe_tasks(cluster=ECS_CLUSTER, tasks=[task_arn])
                for task in describe.get("tasks", []):
                    for tag in task.get("tags", []):
                        if tag["key"] == "pod_id" and tag["value"] == pod_id:
                            ecs.stop_task(
                                cluster=ECS_CLUSTER,
                                task=task_arn,
                                reason="Admin stopped",
                            )
                            logger.info(f"[Deploy] Pod {pod_id} stopped")
                            return {
                                "success": True,
                                "message": f"GPUBROKER POD {pod_id} detenido",
                            }

            return {"success": False, "error": f"Pod {pod_id} no encontrado"}

        except Exception as e:
            logger.error(f"[Deploy] Error stopping pod: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_pod_metrics(pod_id: str) -> dict[str, Any]:
        """
        Get AWS metrics for a pod.

        Args:
            pod_id: Pod identifier

        Returns:
            Dict with metrics
        """
        from datetime import datetime, timedelta

        ecs = _get_boto3_client("ecs")
        cloudwatch = _get_boto3_client("cloudwatch")

        metrics = {
            "pod_id": pod_id,
            "public_ip": None,
            "private_ip": None,
            "cpu_utilization": 0,
            "memory_utilization": 0,
            "uptime_seconds": 0,
            "task_arn": None,
            "status": "unknown",
        }

        if not ecs or not cloudwatch:
            # Mock metrics
            metrics.update(
                {
                    "cpu_utilization": 25.5,
                    "memory_utilization": 45.2,
                    "uptime_seconds": 3600,
                    "status": "running",
                }
            )
            return {"success": True, **metrics}

        try:
            # Find ECS task
            tasks = ecs.list_tasks(cluster=ECS_CLUSTER)
            for task_arn in tasks.get("taskArns", []):
                desc = ecs.describe_tasks(cluster=ECS_CLUSTER, tasks=[task_arn])
                for task in desc.get("tasks", []):
                    for tag in task.get("tags", []):
                        if tag["key"] == "pod_id" and tag["value"] == pod_id:
                            metrics["task_arn"] = task_arn
                            metrics["status"] = task.get("lastStatus", "unknown")

                            # Calculate uptime
                            started = task.get("startedAt")
                            if started:
                                uptime = datetime.now(started.tzinfo) - started
                                metrics["uptime_seconds"] = int(uptime.total_seconds())

                            # Get network interface for IP
                            for att in task.get("attachments", []):
                                if att["type"] == "ElasticNetworkInterface":
                                    for detail in att.get("details", []):
                                        if detail["name"] == "networkInterfaceId":
                                            ec2 = _get_boto3_client("ec2")
                                            if ec2:
                                                eni = ec2.describe_network_interfaces(
                                                    NetworkInterfaceIds=[
                                                        detail["value"]
                                                    ]
                                                )
                                                for ni in eni.get(
                                                    "NetworkInterfaces", []
                                                ):
                                                    metrics["public_ip"] = ni.get(
                                                        "Association", {}
                                                    ).get("PublicIp")
                                                    metrics["private_ip"] = ni.get(
                                                        "PrivateIpAddress"
                                                    )
                            break

            # Get CloudWatch metrics
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=5)

            # CPU
            cpu_resp = cloudwatch.get_metric_statistics(
                Namespace="AWS/ECS",
                MetricName="CPUUtilization",
                Dimensions=[
                    {"Name": "ClusterName", "Value": ECS_CLUSTER},
                    {"Name": "ServiceName", "Value": f"gpubroker-{pod_id}"},
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Average"],
            )
            if cpu_resp.get("Datapoints"):
                metrics["cpu_utilization"] = round(
                    cpu_resp["Datapoints"][-1]["Average"], 1
                )

            # Memory
            mem_resp = cloudwatch.get_metric_statistics(
                Namespace="AWS/ECS",
                MetricName="MemoryUtilization",
                Dimensions=[
                    {"Name": "ClusterName", "Value": ECS_CLUSTER},
                    {"Name": "ServiceName", "Value": f"gpubroker-{pod_id}"},
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Average"],
            )
            if mem_resp.get("Datapoints"):
                metrics["memory_utilization"] = round(
                    mem_resp["Datapoints"][-1]["Average"], 1
                )

            return {"success": True, **metrics}

        except Exception as e:
            logger.error(f"[Deploy] Error getting metrics: {e}")
            return {"success": False, "error": str(e), **metrics}
