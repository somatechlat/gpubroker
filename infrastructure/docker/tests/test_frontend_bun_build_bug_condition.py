"""
Bug Condition Exploration Test for Frontend Bun Build Fix

**Validates: Requirements 2.1, 2.2, 2.3**

**Property 1: Fault Condition - Frontend Service npm Command Fails in Bun Container**

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

This test encodes the expected behavior - it will validate the fix when it passes
after implementation.

GOAL: Surface counterexamples that demonstrate the npm/Bun mismatch bug exists.

Test implementation verifies:
- docker-compose.yml should use `bun run dev` command (NOT `npm run dev`)
- Frontend Containerfile uses Bun runtime (`oven/bun:1`)
- Command override should match the container's available runtime
- Frontend service should be able to start successfully with Bun command
"""

import os
import subprocess
from pathlib import Path

import pytest
import yaml


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class TestFrontendBunBuildBugCondition:
    """
    Bug condition exploration test for frontend Bun build fix.
    
    This test verifies the EXPECTED BEHAVIOR after the fix:
    - docker-compose.yml uses `bun run dev` command
    - Command matches the Bun runtime in Containerfile
    - No npm commands in Bun-based container
    
    On UNFIXED code, this test will FAIL, confirming the bug exists.
    On FIXED code, this test will PASS, confirming the bug is resolved.
    """
    
    def test_docker_compose_should_use_bun_command(self):
        """
        Verify docker-compose.yml uses `bun run dev` command for frontend service.
        
        **Validates: Requirements 2.1, 2.2**
        
        EXPECTED BEHAVIOR: frontend service should have `command: bun run dev`
        BUG CONDITION: frontend service has `command: npm run dev` (npm not available in Bun container)
        """
        docker_compose_path = PROJECT_ROOT / "infrastructure" / "docker" / "docker-compose.yml"
        
        assert docker_compose_path.exists(), (
            f"docker-compose.yml not found at {docker_compose_path}"
        )
        
        # Parse docker-compose.yml
        with open(docker_compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        # Check frontend service exists
        assert 'services' in compose_config, "No services defined in docker-compose.yml"
        assert 'frontend' in compose_config['services'], "Frontend service not found in docker-compose.yml"
        
        frontend_service = compose_config['services']['frontend']
        
        # Check command field
        assert 'command' in frontend_service, (
            f"Frontend service has no command override. "
            f"Expected: command should be 'bun run dev' to match Bun runtime."
        )
        
        command = frontend_service['command']
        
        # Verify it's using bun, not npm
        assert 'bun' in command.lower(), (
            f"Frontend service command does NOT use Bun: '{command}'. "
            f"This indicates the npm/Bun mismatch bug. "
            f"Expected: 'bun run dev' (matches Bun runtime in Containerfile). "
            f"Actual: '{command}' (npm is not available in oven/bun:1 container). "
            f"File: {docker_compose_path}"
        )
        
        assert 'npm' not in command.lower(), (
            f"Frontend service command uses npm: '{command}'. "
            f"This is the BUG CONDITION - npm is not installed in Bun container. "
            f"Expected: 'bun run dev' (matches Bun runtime in Containerfile). "
            f"Actual: '{command}' (will fail with 'npm: command not found'). "
            f"File: {docker_compose_path}"
        )
        
        # Verify exact command format
        expected_commands = ['bun run dev', 'bun run dev']
        assert command in expected_commands, (
            f"Frontend service command format incorrect: '{command}'. "
            f"Expected one of: {expected_commands}. "
            f"File: {docker_compose_path}"
        )
    
    def test_containerfile_uses_bun_runtime(self):
        """
        Verify frontend Containerfile uses Bun runtime.
        
        **Validates: Requirements 2.2, 2.3**
        
        EXPECTED BEHAVIOR: Containerfile should use `oven/bun:1` base image
        """
        containerfile_path = PROJECT_ROOT / "frontend" / "Containerfile"
        
        assert containerfile_path.exists(), (
            f"Frontend Containerfile not found at {containerfile_path}"
        )
        
        containerfile_content = containerfile_path.read_text()
        
        # Check for Bun base image
        assert 'FROM oven/bun:1' in containerfile_content, (
            f"Frontend Containerfile does NOT use Bun base image. "
            f"Expected: 'FROM oven/bun:1' in Containerfile. "
            f"File: {containerfile_path}"
        )
        
        # Check for bun install command
        assert 'bun install' in containerfile_content, (
            f"Frontend Containerfile does NOT use 'bun install'. "
            f"Expected: 'RUN bun install' in Containerfile. "
            f"File: {containerfile_path}"
        )
        
        # Check for bun run dev in CMD
        assert 'CMD ["bun", "run", "dev"]' in containerfile_content, (
            f"Frontend Containerfile does NOT use 'bun run dev' as default CMD. "
            f"Expected: 'CMD [\"bun\", \"run\", \"dev\"]' in Containerfile. "
            f"File: {containerfile_path}"
        )
    
    def test_docker_compose_command_matches_containerfile_runtime(self):
        """
        Verify docker-compose.yml command override matches Containerfile runtime.
        
        **Validates: Requirements 2.1, 2.2, 2.3**
        
        EXPECTED BEHAVIOR: Command override should use same runtime as Containerfile (Bun)
        BUG CONDITION: Command override uses npm, but Containerfile uses Bun
        """
        docker_compose_path = PROJECT_ROOT / "infrastructure" / "docker" / "docker-compose.yml"
        containerfile_path = PROJECT_ROOT / "frontend" / "Containerfile"
        
        # Parse docker-compose.yml
        with open(docker_compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        frontend_service = compose_config['services']['frontend']
        command = frontend_service.get('command', '')
        
        # Read Containerfile
        containerfile_content = containerfile_path.read_text()
        
        # If Containerfile uses Bun, command should use Bun
        if 'FROM oven/bun:1' in containerfile_content:
            assert 'bun' in command.lower(), (
                f"Runtime mismatch detected (BUG CONDITION). "
                f"Containerfile uses Bun runtime (oven/bun:1), "
                f"but docker-compose.yml command uses: '{command}'. "
                f"Expected: Command should use 'bun run dev' to match Bun runtime. "
                f"Actual: Command uses npm, which is NOT installed in Bun container. "
                f"This will cause 'npm: command not found' error on startup. "
                f"Files: {docker_compose_path}, {containerfile_path}"
            )
            
            assert 'npm' not in command.lower(), (
                f"Runtime mismatch detected (BUG CONDITION). "
                f"Containerfile uses Bun runtime (oven/bun:1), "
                f"but docker-compose.yml command uses npm: '{command}'. "
                f"npm is NOT installed in oven/bun:1 container. "
                f"Expected: 'bun run dev'. "
                f"Actual: '{command}' (will fail with 'npm: command not found'). "
                f"Files: {docker_compose_path}, {containerfile_path}"
            )
    
    def test_dev_compose_has_no_command_override(self):
        """
        Verify docker-compose.dev.yml does NOT override the command.
        
        **Validates: Requirements 3.1 (Preservation)**
        
        EXPECTED BEHAVIOR: docker-compose.dev.yml should use Containerfile default CMD
        """
        dev_compose_path = PROJECT_ROOT / "infrastructure" / "docker" / "docker-compose.dev.yml"
        
        if not dev_compose_path.exists():
            pytest.skip(f"docker-compose.dev.yml not found at {dev_compose_path}")
        
        # Parse docker-compose.dev.yml
        with open(dev_compose_path, 'r') as f:
            dev_compose_config = yaml.safe_load(f)
        
        # Check if frontend service exists
        if 'services' not in dev_compose_config or 'frontend' not in dev_compose_config['services']:
            pytest.skip("Frontend service not defined in docker-compose.dev.yml")
        
        frontend_service = dev_compose_config['services']['frontend']
        
        # Verify no command override (should use Containerfile default)
        assert 'command' not in frontend_service, (
            f"docker-compose.dev.yml should NOT override the command. "
            f"Expected: No command field (use Containerfile default CMD). "
            f"Actual: command = '{frontend_service.get('command')}'. "
            f"File: {dev_compose_path}"
        )
    
    def test_frontend_service_configuration_preserved(self):
        """
        Verify frontend service configuration is preserved (except command).
        
        **Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6 (Preservation)**
        
        EXPECTED BEHAVIOR: All frontend service config except command should remain unchanged
        """
        docker_compose_path = PROJECT_ROOT / "infrastructure" / "docker" / "docker-compose.yml"
        
        # Parse docker-compose.yml
        with open(docker_compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        frontend_service = compose_config['services']['frontend']
        
        # Verify build context
        assert 'build' in frontend_service, "Frontend service missing build configuration"
        assert frontend_service['build']['context'] == '../../frontend', (
            f"Frontend build context changed. "
            f"Expected: '../../frontend'. "
            f"Actual: '{frontend_service['build']['context']}'"
        )
        
        # Verify container name
        assert frontend_service.get('container_name') == 'gpubroker_frontend', (
            f"Frontend container name changed. "
            f"Expected: 'gpubroker_frontend'. "
            f"Actual: '{frontend_service.get('container_name')}'"
        )
        
        # Verify environment variables
        assert 'environment' in frontend_service, "Frontend service missing environment configuration"
        env = frontend_service['environment']
        assert 'VITE_API_URL' in env, "Frontend missing VITE_API_URL environment variable"
        assert 'VITE_WS_URL' in env, "Frontend missing VITE_WS_URL environment variable"
        
        # Verify ports
        assert 'ports' in frontend_service, "Frontend service missing ports configuration"
        ports = frontend_service['ports']
        assert len(ports) > 0, "Frontend service has no port mappings"
        # Port format: "${PORT_FRONTEND:-28030}:3000"
        assert ':3000' in str(ports[0]), (
            f"Frontend container port changed. "
            f"Expected: port 3000 exposed. "
            f"Actual: '{ports[0]}'"
        )
        
        # Verify volumes
        assert 'volumes' in frontend_service, "Frontend service missing volumes configuration"
        volumes = frontend_service['volumes']
        assert len(volumes) >= 2, (
            f"Frontend service missing volume mounts. "
            f"Expected: at least 2 volumes (app directory and node_modules). "
            f"Actual: {len(volumes)} volumes"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
