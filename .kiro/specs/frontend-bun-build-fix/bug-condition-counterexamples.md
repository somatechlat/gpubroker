# Bug Condition Exploration - Counterexamples

## Test Execution Summary

**Date**: 2026-01-08
**Test File**: `infrastructure/docker/tests/test_frontend_bun_build_bug_condition.py`
**Status**: ✅ Test FAILED as expected (confirms bug exists)

## Counterexamples Found

### 1. Frontend Service Uses npm Command in Bun Container

**Test**: `test_docker_compose_should_use_bun_command`
**Status**: FAILED ✅ (Expected - confirms bug)

**Bug Condition Detected**:
```
Frontend service command does NOT use Bun: 'npm run dev'. 
This indicates the npm/Bun mismatch bug. 
Expected: 'bun run dev' (matches Bun runtime in Containerfile). 
Actual: 'npm run dev' (npm is not available in oven/bun:1 container). 
File: infrastructure/docker/docker-compose.yml
```

**Root Cause**: 
- docker-compose.yml line 166 has `command: npm run dev`
- Frontend Containerfile uses `FROM oven/bun:1` (Bun runtime only)
- npm is NOT installed in the oven/bun:1 container image
- This will cause "npm: command not found" error when the service starts

### 2. Runtime Mismatch Between Compose and Containerfile

**Test**: `test_docker_compose_command_matches_containerfile_runtime`
**Status**: FAILED ✅ (Expected - confirms bug)

**Bug Condition Detected**:
```
Runtime mismatch detected (BUG CONDITION). 
Containerfile uses Bun runtime (oven/bun:1), 
but docker-compose.yml command uses: 'npm run dev'. 
Expected: Command should use 'bun run dev' to match Bun runtime. 
Actual: Command uses npm, which is NOT installed in Bun container. 
This will cause 'npm: command not found' error on startup.
```

**Root Cause**:
- Containerfile correctly uses Bun: `FROM oven/bun:1`, `RUN bun install`, `CMD ["bun", "run", "dev"]`
- docker-compose.yml overrides with incompatible npm command
- This creates a runtime mismatch where the command doesn't match the available runtime

## Passing Tests (Preservation Verification)

### 3. Containerfile Uses Bun Runtime

**Test**: `test_containerfile_uses_bun_runtime`
**Status**: PASSED ✅

**Verification**:
- Containerfile uses `FROM oven/bun:1` ✓
- Containerfile uses `RUN bun install` ✓
- Containerfile uses `CMD ["bun", "run", "dev"]` ✓

This confirms the Containerfile is correctly configured for Bun.

### 4. Dev Compose Has No Command Override

**Test**: `test_dev_compose_has_no_command_override`
**Status**: PASSED ✅

**Verification**:
- docker-compose.dev.yml does NOT override the command ✓
- Uses Containerfile default CMD (bun run dev) ✓

This confirms the development compose file works correctly.

### 5. Frontend Service Configuration Preserved

**Test**: `test_frontend_service_configuration_preserved`
**Status**: PASSED ✅

**Verification**:
- Build context: `../../frontend` ✓
- Container name: `gpubroker_frontend` ✓
- Environment variables: VITE_API_URL, VITE_WS_URL ✓
- Port mapping: 3000 exposed ✓
- Volumes: app directory and node_modules mounted ✓

This confirms all other frontend service configuration is correct.

## Conclusion

The bug condition exploration test successfully identified the bug:

1. **Bug Confirmed**: docker-compose.yml uses `npm run dev` command override
2. **Root Cause Confirmed**: npm is not available in oven/bun:1 container
3. **Impact**: Frontend service will fail to start with "npm: command not found" error
4. **Fix Required**: Change command from `npm run dev` to `bun run dev`

The test encodes the expected behavior (using Bun commands) and will PASS once the fix is implemented, confirming the bug is resolved.

## Next Steps

1. ✅ Bug condition exploration test written and run
2. ✅ Counterexamples documented
3. ⏭️ Write preservation property tests (Task 2)
4. ⏭️ Implement fix (Task 3)
5. ⏭️ Verify tests pass after fix
