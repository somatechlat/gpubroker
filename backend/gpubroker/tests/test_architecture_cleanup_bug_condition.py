"""
Bug Condition Exploration Test for Architecture Cleanup

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7**

**Property 1: Fault Condition - Duplicate Architecture Detection**

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

This test encodes the expected behavior - it will validate the fix when it passes
after implementation.

GOAL: Surface counterexamples that demonstrate the duplicate architecture bug exists.

Test implementation verifies:
- OLD apps directory should NOT exist (backend/gpubroker/apps/)
- POD SaaS directory should exist (backend/gpubroker/gpubrokerpod/)
- Django settings should reference POD SaaS apps only
- ASGI should import from POD SaaS only
- No OLD imports should remain in codebase
"""

import os
import subprocess
from pathlib import Path

import pytest


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class TestArchitectureCleanupBugCondition:
    """
    Bug condition exploration test for duplicate architecture cleanup.
    
    This test verifies the EXPECTED BEHAVIOR after the fix:
    - Only POD SaaS architecture exists
    - Django settings reference POD SaaS apps
    - ASGI imports from POD SaaS
    - No OLD imports remain
    
    On UNFIXED code, this test will FAIL, confirming the bug exists.
    On FIXED code, this test will PASS, confirming the bug is resolved.
    """
    
    def test_old_apps_directory_should_not_exist(self):
        """
        Verify OLD marketplace architecture directory does NOT exist.
        
        **Validates: Requirements 1.2, 2.2, 2.8**
        
        EXPECTED BEHAVIOR: backend/gpubroker/apps/ should NOT exist
        BUG CONDITION: backend/gpubroker/apps/ exists (duplicate architecture)
        """
        old_apps_path = PROJECT_ROOT / "backend" / "gpubroker" / "apps"
        
        assert not old_apps_path.exists(), (
            f"OLD architecture directory exists at {old_apps_path}. "
            f"This indicates duplicate architecture bug. "
            f"Expected: Directory should be removed. "
            f"Actual: Directory exists with contents: {list(old_apps_path.iterdir()) if old_apps_path.exists() else []}"
        )
    
    def test_pod_saas_directory_exists(self):
        """
        Verify POD SaaS architecture directory exists.
        
        **Validates: Requirements 2.2**
        
        EXPECTED BEHAVIOR: backend/gpubroker/gpubrokerpod/ should exist
        """
        pod_saas_path = PROJECT_ROOT / "backend" / "gpubroker" / "gpubrokerpod"
        
        assert pod_saas_path.exists(), (
            f"POD SaaS architecture directory does NOT exist at {pod_saas_path}. "
            f"Expected: Directory should exist with POD SaaS implementation."
        )
        
        # Verify key POD SaaS apps exist
        gpubrokerapp_path = pod_saas_path / "gpubrokerapp" / "apps"
        assert gpubrokerapp_path.exists(), (
            f"POD SaaS apps directory does NOT exist at {gpubrokerapp_path}"
        )
    
    def test_django_settings_should_not_reference_old_architecture(self):
        """
        Verify Django settings do NOT reference OLD architecture apps.
        
        **Validates: Requirements 1.1, 2.1, 2.6**
        
        EXPECTED BEHAVIOR: INSTALLED_APPS should NOT contain apps.auth_app, apps.providers, apps.security
        BUG CONDITION: INSTALLED_APPS contains OLD architecture references
        """
        settings_path = PROJECT_ROOT / "backend" / "gpubroker" / "gpubroker" / "settings" / "base.py"
        
        assert settings_path.exists(), f"Django settings file not found at {settings_path}"
        
        settings_content = settings_path.read_text()
        
        # Check for OLD architecture references
        old_references = []
        if '"apps.auth_app"' in settings_content or "'apps.auth_app'" in settings_content:
            old_references.append("apps.auth_app")
        if '"apps.providers"' in settings_content or "'apps.providers'" in settings_content:
            old_references.append("apps.providers")
        if '"apps.security"' in settings_content or "'apps.security'" in settings_content:
            old_references.append("apps.security")
        
        assert len(old_references) == 0, (
            f"Django settings contain OLD architecture references: {old_references}. "
            f"This indicates duplicate architecture bug. "
            f"Expected: Settings should reference POD SaaS apps only. "
            f"File: {settings_path}"
        )
    
    def test_django_settings_should_reference_pod_saas_architecture(self):
        """
        Verify Django settings reference POD SaaS architecture apps.
        
        **Validates: Requirements 2.1, 2.6**
        
        EXPECTED BEHAVIOR: INSTALLED_APPS should contain gpubrokerpod.gpubrokerapp.apps.*
        """
        settings_path = PROJECT_ROOT / "backend" / "gpubroker" / "gpubroker" / "settings" / "base.py"
        
        assert settings_path.exists(), f"Django settings file not found at {settings_path}"
        
        settings_content = settings_path.read_text()
        
        # Check for POD SaaS architecture references
        pod_saas_references = [
            "gpubrokerpod.gpubrokerapp.apps.auth_app",
            "gpubrokerpod.gpubrokerapp.apps.providers",
            "gpubrokerpod.gpubrokerapp.apps.billing",
            "gpubrokerpod.gpubrokerapp.apps.deployment",
        ]
        
        found_references = []
        for ref in pod_saas_references:
            if f'"{ref}"' in settings_content or f"'{ref}'" in settings_content:
                found_references.append(ref)
        
        assert len(found_references) > 0, (
            f"Django settings do NOT contain POD SaaS architecture references. "
            f"Expected at least one of: {pod_saas_references}. "
            f"Found: {found_references}. "
            f"File: {settings_path}"
        )
    
    def test_asgi_should_not_import_from_old_architecture(self):
        """
        Verify ASGI configuration does NOT import from OLD architecture.
        
        **Validates: Requirements 1.4, 2.4**
        
        EXPECTED BEHAVIOR: ASGI should import from gpubrokerpod.gpubrokerapp.apps.websocket_gateway
        BUG CONDITION: ASGI imports from apps.websocket_gateway
        """
        asgi_path = PROJECT_ROOT / "backend" / "gpubroker" / "gpubroker" / "asgi.py"
        
        assert asgi_path.exists(), f"ASGI configuration file not found at {asgi_path}"
        
        asgi_content = asgi_path.read_text()
        
        # Check for OLD architecture import
        old_import = "from apps.websocket_gateway"
        
        assert old_import not in asgi_content, (
            f"ASGI configuration imports from OLD architecture: '{old_import}'. "
            f"This indicates duplicate architecture bug. "
            f"Expected: ASGI should import from POD SaaS (gpubrokerpod.gpubrokerapp.apps.websocket_gateway). "
            f"File: {asgi_path}"
        )
    
    def test_asgi_should_import_from_pod_saas_architecture(self):
        """
        Verify ASGI configuration imports from POD SaaS architecture.
        
        **Validates: Requirements 2.4**
        
        EXPECTED BEHAVIOR: ASGI should import from gpubrokerpod.gpubrokerapp.apps.websocket_gateway
        """
        asgi_path = PROJECT_ROOT / "backend" / "gpubroker" / "gpubroker" / "asgi.py"
        
        assert asgi_path.exists(), f"ASGI configuration file not found at {asgi_path}"
        
        asgi_content = asgi_path.read_text()
        
        # Check for POD SaaS import
        pod_saas_import = "from gpubrokerpod.gpubrokerapp.apps.websocket_gateway"
        
        assert pod_saas_import in asgi_content, (
            f"ASGI configuration does NOT import from POD SaaS architecture. "
            f"Expected: '{pod_saas_import}' in ASGI configuration. "
            f"File: {asgi_path}"
        )
    
    def test_no_old_imports_in_test_files(self):
        """
        Verify test files do NOT import from OLD architecture.
        
        **Validates: Requirements 1.5, 2.3, 2.5**
        
        EXPECTED BEHAVIOR: No test files should import from apps.*
        BUG CONDITION: Test files import from apps.providers.adapters.registry, etc.
        """
        tests_dir = PROJECT_ROOT / "backend" / "gpubroker" / "tests"
        
        assert tests_dir.exists(), f"Tests directory not found at {tests_dir}"
        
        # Search for OLD imports in test files
        old_import_pattern = "from apps\\."
        
        try:
            result = subprocess.run(
                ["grep", "-r", old_import_pattern, str(tests_dir), "--include=*.py"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            # grep returns 0 if matches found, 1 if no matches, 2+ for errors
            if result.returncode == 0:
                # Matches found - this is the bug condition
                matches = result.stdout.strip().split('\n')
                assert False, (
                    f"Test files contain OLD architecture imports (from apps.*). "
                    f"This indicates duplicate architecture bug. "
                    f"Found {len(matches)} OLD imports in test files:\n"
                    f"{result.stdout[:1000]}"  # Limit output
                )
            elif result.returncode == 1:
                # No matches - this is expected behavior
                pass
            else:
                # Error occurred
                pytest.skip(f"grep command failed: {result.stderr}")
        
        except FileNotFoundError:
            pytest.skip("grep command not available on this system")
    
    def test_no_old_imports_in_codebase(self):
        """
        Verify entire codebase does NOT import from OLD architecture.
        
        **Validates: Requirements 1.3, 2.3**
        
        EXPECTED BEHAVIOR: No Python files should import from apps.*
        BUG CONDITION: Python files import from apps.* (mixed imports)
        """
        backend_dir = PROJECT_ROOT / "backend" / "gpubroker"
        
        assert backend_dir.exists(), f"Backend directory not found at {backend_dir}"
        
        # Search for OLD imports in entire backend
        old_import_pattern = "from apps\\."
        
        try:
            result = subprocess.run(
                ["grep", "-r", old_import_pattern, str(backend_dir), "--include=*.py"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            # grep returns 0 if matches found, 1 if no matches, 2+ for errors
            if result.returncode == 0:
                # Matches found - this is the bug condition
                matches = result.stdout.strip().split('\n')
                
                # Filter out this test file itself
                filtered_matches = [
                    m for m in matches 
                    if "test_architecture_cleanup_bug_condition.py" not in m
                ]
                
                if filtered_matches:
                    assert False, (
                        f"Codebase contains OLD architecture imports (from apps.*). "
                        f"This indicates duplicate architecture bug. "
                        f"Found {len(filtered_matches)} OLD imports:\n"
                        f"{chr(10).join(filtered_matches[:20])}"  # Show first 20 matches
                    )
            elif result.returncode == 1:
                # No matches - this is expected behavior
                pass
            else:
                # Error occurred
                pytest.skip(f"grep command failed: {result.stderr}")
        
        except FileNotFoundError:
            pytest.skip("grep command not available on this system")
    
    def test_django_check_passes(self):
        """
        Verify Django configuration check passes.
        
        **Validates: Requirements 2.6, 2.8, 3.9**
        
        EXPECTED BEHAVIOR: python manage.py check should pass with no errors
        """
        manage_py = PROJECT_ROOT / "backend" / "gpubroker" / "manage.py"
        
        assert manage_py.exists(), f"manage.py not found at {manage_py}"
        
        try:
            result = subprocess.run(
                ["python", str(manage_py), "check"],
                capture_output=True,
                text=True,
                cwd=manage_py.parent,
                timeout=30
            )
            
            assert result.returncode == 0, (
                f"Django check failed. This may indicate configuration issues. "
                f"Return code: {result.returncode}\n"
                f"STDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}"
            )
        
        except subprocess.TimeoutExpired:
            pytest.skip("Django check timed out")
        except FileNotFoundError:
            pytest.skip("Python command not available")
