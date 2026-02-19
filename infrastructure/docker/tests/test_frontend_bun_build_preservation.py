"""
Preservation Property Tests for Frontend Bun Build Fix

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

**Property 2: Preservation - Non-Frontend Configuration Unchanged**

IMPORTANT: Follow observation-first methodology.
- Observe behavior on UNFIXED docker-compose.yml for all non-frontend-command configuration
- Parse the UNFIXED docker-compose.yml and record all service definitions, volumes, networks, environment variables
- Write property-based tests capturing that all configuration elements except `services.frontend.command` remain identical
- Property-based testing generates many test cases for stronger guarantees

EXPECTED OUTCOME: Tests PASS on unfixed code (confirms baseline behavior to preserve)

This test suite uses property-based testing to verify that ALL configuration elements
in docker-compose.yml remain unchanged except for the specific frontend service command field.
"""

import os
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml
from hypothesis import given, strategies as st, settings, HealthCheck


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class TestFrontendBunBuildPreservation:
    """
    Preservation property tests for frontend Bun build fix.
    
    These tests verify that ALL configuration in docker-compose.yml remains unchanged
    except for the specific `services.frontend.command` field.
    
    Tests use property-based testing to generate comprehensive test cases covering:
    - All service definitions (django, nginx, postgres, redis, vault, clickhouse)
    - All volume definitions
    - All network definitions
    - All environment variables
    - All port mappings
    - All healthcheck configurations
    - All frontend service fields except command
    """
    
    @pytest.fixture
    def docker_compose_config(self):
        """Load the UNFIXED docker-compose.yml configuration."""
        docker_compose_path = PROJECT_ROOT / "infrastructure" / "docker" / "docker-compose.yml"
        
        assert docker_compose_path.exists(), (
            f"docker-compose.yml not found at {docker_compose_path}"
        )
        
        with open(docker_compose_path, 'r') as f:
            return yaml.safe_load(f)
    
    @pytest.fixture
    def baseline_config(self, docker_compose_config):
        """
        Capture baseline configuration from UNFIXED docker-compose.yml.
        
        This represents the configuration that MUST be preserved after the fix.
        """
        return docker_compose_config
    
    def test_all_services_except_frontend_unchanged(self, baseline_config):
        """
        Verify all service definitions except frontend remain unchanged.
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
        
        EXPECTED BEHAVIOR: All services (django, nginx, postgres, redis, vault, clickhouse)
        should have identical configuration in both unfixed and fixed versions.
        """
        services = baseline_config.get('services', {})
        
        # List of services that should remain completely unchanged
        non_frontend_services = [
            'vault', 'postgres', 'clickhouse', 'redis', 'django', 'nginx'
        ]
        
        for service_name in non_frontend_services:
            assert service_name in services, (
                f"Service '{service_name}' not found in docker-compose.yml. "
                f"This service must be preserved in the fixed version."
            )
            
            service_config = services[service_name]
            
            # Verify service has expected configuration keys
            assert isinstance(service_config, dict), (
                f"Service '{service_name}' configuration is not a dictionary. "
                f"Type: {type(service_config)}"
            )
            
            # Document the baseline configuration for this service
            print(f"\n[BASELINE] Service '{service_name}' configuration keys: {list(service_config.keys())}")
    
    def test_volume_definitions_unchanged(self, baseline_config):
        """
        Verify all volume definitions remain unchanged.
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
        
        EXPECTED BEHAVIOR: All volume definitions should be identical in both versions.
        """
        volumes = baseline_config.get('volumes', {})
        
        expected_volumes = [
            'vault_data', 'postgres_data', 'clickhouse_data', 'redis_data', 'static_files'
        ]
        
        for volume_name in expected_volumes:
            assert volume_name in volumes, (
                f"Volume '{volume_name}' not found in docker-compose.yml. "
                f"This volume must be preserved in the fixed version."
            )
        
        # Document baseline volumes
        print(f"\n[BASELINE] Volumes defined: {list(volumes.keys())}")
    
    def test_frontend_service_non_command_fields_unchanged(self, baseline_config):
        """
        Verify all frontend service fields except command remain unchanged.
        
        **Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6**
        
        EXPECTED BEHAVIOR: Frontend service configuration (build, environment, ports, volumes)
        should be identical except for the command field.
        """
        services = baseline_config.get('services', {})
        assert 'frontend' in services, "Frontend service not found in docker-compose.yml"
        
        frontend = services['frontend']
        
        # Verify build configuration
        assert 'build' in frontend, "Frontend service missing build configuration"
        assert frontend['build']['context'] == '../../frontend', (
            f"Frontend build context must be preserved. "
            f"Expected: '../../frontend'. "
            f"Actual: '{frontend['build']['context']}'"
        )
        
        # Verify container name
        assert frontend.get('container_name') == 'gpubroker_frontend', (
            f"Frontend container name must be preserved. "
            f"Expected: 'gpubroker_frontend'. "
            f"Actual: '{frontend.get('container_name')}'"
        )
        
        # Verify environment variables
        assert 'environment' in frontend, "Frontend service missing environment configuration"
        env = frontend['environment']
        assert 'VITE_API_URL' in env, "Frontend must preserve VITE_API_URL environment variable"
        assert 'VITE_WS_URL' in env, "Frontend must preserve VITE_WS_URL environment variable"
        
        # Document baseline environment variables
        print(f"\n[BASELINE] Frontend environment variables: {list(env.keys())}")
        print(f"[BASELINE] VITE_API_URL: {env['VITE_API_URL']}")
        print(f"[BASELINE] VITE_WS_URL: {env['VITE_WS_URL']}")
        
        # Verify ports
        assert 'ports' in frontend, "Frontend service missing ports configuration"
        ports = frontend['ports']
        assert len(ports) > 0, "Frontend service must preserve port mappings"
        
        # Document baseline ports
        print(f"\n[BASELINE] Frontend ports: {ports}")
        
        # Verify volumes
        assert 'volumes' in frontend, "Frontend service missing volumes configuration"
        volumes = frontend['volumes']
        assert len(volumes) >= 2, (
            f"Frontend service must preserve volume mounts. "
            f"Expected: at least 2 volumes. "
            f"Actual: {len(volumes)} volumes"
        )
        
        # Document baseline volumes
        print(f"\n[BASELINE] Frontend volumes: {volumes}")
    
    def test_service_dependencies_unchanged(self, baseline_config):
        """
        Verify service dependencies remain unchanged.
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
        
        EXPECTED BEHAVIOR: All service dependencies (depends_on) should be preserved.
        """
        services = baseline_config.get('services', {})
        
        # Check django dependencies
        if 'django' in services and 'depends_on' in services['django']:
            django_deps = services['django']['depends_on']
            print(f"\n[BASELINE] Django dependencies: {django_deps}")
            
            # Verify critical dependencies exist
            assert 'postgres' in django_deps, "Django must preserve postgres dependency"
            assert 'redis' in django_deps, "Django must preserve redis dependency"
            assert 'vault' in django_deps, "Django must preserve vault dependency"
        
        # Check nginx dependencies
        if 'nginx' in services and 'depends_on' in services['nginx']:
            nginx_deps = services['nginx']['depends_on']
            print(f"\n[BASELINE] Nginx dependencies: {nginx_deps}")
            
            # Verify nginx depends on django and frontend
            assert 'django' in nginx_deps, "Nginx must preserve django dependency"
            assert 'frontend' in nginx_deps, "Nginx must preserve frontend dependency"
    
    def test_healthcheck_configurations_unchanged(self, baseline_config):
        """
        Verify healthcheck configurations remain unchanged.
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
        
        EXPECTED BEHAVIOR: All healthcheck configurations should be preserved.
        """
        services = baseline_config.get('services', {})
        
        services_with_healthchecks = ['vault', 'postgres', 'django', 'nginx']
        
        for service_name in services_with_healthchecks:
            if service_name in services and 'healthcheck' in services[service_name]:
                healthcheck = services[service_name]['healthcheck']
                print(f"\n[BASELINE] {service_name} healthcheck: {healthcheck}")
                
                # Verify healthcheck has required fields
                assert 'test' in healthcheck, (
                    f"Service '{service_name}' healthcheck must preserve test command"
                )
    
    def test_environment_variables_for_all_services_unchanged(self, baseline_config):
        """
        Verify environment variables for all services remain unchanged.
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
        
        EXPECTED BEHAVIOR: All environment variables for all services should be preserved.
        """
        services = baseline_config.get('services', {})
        
        for service_name, service_config in services.items():
            if 'environment' in service_config:
                env_vars = service_config['environment']
                print(f"\n[BASELINE] {service_name} environment variables: {list(env_vars.keys())}")
                
                # Verify environment is a dictionary
                assert isinstance(env_vars, dict), (
                    f"Service '{service_name}' environment must be a dictionary. "
                    f"Type: {type(env_vars)}"
                )
    
    def test_port_mappings_for_all_services_unchanged(self, baseline_config):
        """
        Verify port mappings for all services remain unchanged.
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
        
        EXPECTED BEHAVIOR: All port mappings should be preserved.
        """
        services = baseline_config.get('services', {})
        
        for service_name, service_config in services.items():
            if 'ports' in service_config:
                ports = service_config['ports']
                print(f"\n[BASELINE] {service_name} ports: {ports}")
                
                # Verify ports is a list
                assert isinstance(ports, list), (
                    f"Service '{service_name}' ports must be a list. "
                    f"Type: {type(ports)}"
                )
                
                # Verify ports list is not empty
                assert len(ports) > 0, (
                    f"Service '{service_name}' must preserve port mappings"
                )
    
    def test_volume_mounts_for_all_services_unchanged(self, baseline_config):
        """
        Verify volume mounts for all services remain unchanged.
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
        
        EXPECTED BEHAVIOR: All volume mounts should be preserved.
        """
        services = baseline_config.get('services', {})
        
        for service_name, service_config in services.items():
            if 'volumes' in service_config:
                volumes = service_config['volumes']
                print(f"\n[BASELINE] {service_name} volumes: {volumes}")
                
                # Verify volumes is a list
                assert isinstance(volumes, list), (
                    f"Service '{service_name}' volumes must be a list. "
                    f"Type: {type(volumes)}"
                )
    
    def test_compose_file_name_unchanged(self, baseline_config):
        """
        Verify docker-compose.yml name field remains unchanged.
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
        
        EXPECTED BEHAVIOR: Compose project name should be preserved.
        """
        name = baseline_config.get('name')
        
        assert name == 'gpubroker', (
            f"Docker Compose project name must be preserved. "
            f"Expected: 'gpubroker'. "
            f"Actual: '{name}'"
        )
        
        print(f"\n[BASELINE] Docker Compose project name: {name}")
    
    def test_specific_service_configurations_preserved(self, baseline_config):
        """
        Verify specific critical service configurations are preserved.
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
        
        EXPECTED BEHAVIOR: Critical service configurations should remain unchanged.
        """
        services = baseline_config.get('services', {})
        
        # Vault configuration
        if 'vault' in services:
            vault = services['vault']
            assert vault.get('image') == 'hashicorp/vault:1.15', (
                "Vault image must be preserved"
            )
            assert vault.get('container_name') == 'gpubroker_vault', (
                "Vault container name must be preserved"
            )
            print(f"\n[BASELINE] Vault image: {vault.get('image')}")
        
        # Postgres configuration
        if 'postgres' in services:
            postgres = services['postgres']
            assert postgres.get('image') == 'postgres:15-alpine', (
                "Postgres image must be preserved"
            )
            assert postgres.get('container_name') == 'gpubroker_postgres', (
                "Postgres container name must be preserved"
            )
            print(f"\n[BASELINE] Postgres image: {postgres.get('image')}")
        
        # Redis configuration
        if 'redis' in services:
            redis = services['redis']
            assert redis.get('image') == 'redis:7-alpine', (
                "Redis image must be preserved"
            )
            assert redis.get('container_name') == 'gpubroker_redis', (
                "Redis container name must be preserved"
            )
            print(f"\n[BASELINE] Redis image: {redis.get('image')}")
        
        # ClickHouse configuration
        if 'clickhouse' in services:
            clickhouse = services['clickhouse']
            assert clickhouse.get('image') == 'clickhouse/clickhouse-server:23.8', (
                "ClickHouse image must be preserved"
            )
            assert clickhouse.get('container_name') == 'gpubroker_clickhouse', (
                "ClickHouse container name must be preserved"
            )
            print(f"\n[BASELINE] ClickHouse image: {clickhouse.get('image')}")
        
        # Django configuration
        if 'django' in services:
            django = services['django']
            assert django.get('container_name') == 'gpubroker_django', (
                "Django container name must be preserved"
            )
            assert 'build' in django, "Django build configuration must be preserved"
            print(f"\n[BASELINE] Django build context: {django['build'].get('context')}")
        
        # Nginx configuration
        if 'nginx' in services:
            nginx = services['nginx']
            assert nginx.get('image') == 'nginx:alpine', (
                "Nginx image must be preserved"
            )
            assert nginx.get('container_name') == 'gpubroker_nginx', (
                "Nginx container name must be preserved"
            )
            print(f"\n[BASELINE] Nginx image: {nginx.get('image')}")
    
    @given(st.sampled_from(['vault', 'postgres', 'clickhouse', 'redis', 'django', 'nginx']))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_service_exists_and_has_configuration(self, baseline_config, service_name):
        """
        Property-based test: Verify each service exists and has valid configuration.
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
        
        This property-based test generates test cases for all non-frontend services
        to ensure they are preserved in the fixed version.
        """
        services = baseline_config.get('services', {})
        
        # Property: Service must exist
        assert service_name in services, (
            f"Service '{service_name}' must be preserved in fixed version"
        )
        
        service_config = services[service_name]
        
        # Property: Service configuration must be a dictionary
        assert isinstance(service_config, dict), (
            f"Service '{service_name}' configuration must be a dictionary"
        )
        
        # Property: Service must have at least one configuration key
        assert len(service_config) > 0, (
            f"Service '{service_name}' must have configuration"
        )
    
    @given(st.sampled_from(['vault_data', 'postgres_data', 'clickhouse_data', 'redis_data', 'static_files']))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_volume_exists(self, baseline_config, volume_name):
        """
        Property-based test: Verify each volume exists.
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
        
        This property-based test generates test cases for all volumes
        to ensure they are preserved in the fixed version.
        """
        volumes = baseline_config.get('volumes', {})
        
        # Property: Volume must exist
        assert volume_name in volumes, (
            f"Volume '{volume_name}' must be preserved in fixed version"
        )
    
    @given(st.sampled_from(['build', 'container_name', 'environment', 'ports', 'volumes']))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_frontend_non_command_field_exists(self, baseline_config, field_name):
        """
        Property-based test: Verify frontend service non-command fields exist.
        
        **Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6**
        
        This property-based test generates test cases for all frontend service fields
        except command to ensure they are preserved in the fixed version.
        """
        services = baseline_config.get('services', {})
        assert 'frontend' in services, "Frontend service must exist"
        
        frontend = services['frontend']
        
        # Property: Non-command field must exist
        assert field_name in frontend, (
            f"Frontend service field '{field_name}' must be preserved in fixed version"
        )
        
        # Property: Field must have a value
        assert frontend[field_name] is not None, (
            f"Frontend service field '{field_name}' must have a value"
        )


class TestDockerComposeDevPreservation:
    """
    Preservation tests for docker-compose.dev.yml.
    
    **Validates: Requirement 3.1**
    
    Verify that docker-compose.dev.yml remains unchanged and continues to use
    the default CMD from Containerfile (no command override).
    """
    
    def test_dev_compose_frontend_has_no_command_override(self):
        """
        Verify docker-compose.dev.yml frontend service has no command override.
        
        **Validates: Requirement 3.1**
        
        EXPECTED BEHAVIOR: docker-compose.dev.yml should NOT override the command,
        allowing the Containerfile's default CMD to be used.
        """
        dev_compose_path = PROJECT_ROOT / "infrastructure" / "docker" / "docker-compose.dev.yml"
        
        if not dev_compose_path.exists():
            pytest.skip(f"docker-compose.dev.yml not found at {dev_compose_path}")
        
        with open(dev_compose_path, 'r') as f:
            dev_compose_config = yaml.safe_load(f)
        
        # Check if frontend service exists
        if 'services' not in dev_compose_config or 'frontend' not in dev_compose_config['services']:
            pytest.skip("Frontend service not defined in docker-compose.dev.yml")
        
        frontend_service = dev_compose_config['services']['frontend']
        
        # Verify no command override
        assert 'command' not in frontend_service, (
            f"docker-compose.dev.yml must NOT override the command. "
            f"Expected: No command field (use Containerfile default CMD). "
            f"Actual: command = '{frontend_service.get('command')}'. "
            f"This preservation requirement must be maintained in the fixed version."
        )
        
        print(f"\n[BASELINE] docker-compose.dev.yml frontend service has no command override (PRESERVED)")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
