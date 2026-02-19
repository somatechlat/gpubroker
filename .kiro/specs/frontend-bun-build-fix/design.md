# Frontend Bun Build Fix - Bugfix Design

## Overview

The frontend service in `infrastructure/docker/docker-compose.yml` incorrectly overrides the container's default command with `npm run dev`, despite the frontend Containerfile being built on the Bun runtime (`oven/bun:1` image). This creates a runtime mismatch where the container attempts to execute npm commands in an environment where only Bun is installed, causing the frontend service to fail on startup. The fix is straightforward: change the command override from `npm run dev` to `bun run dev` to align with the Containerfile's intended runtime environment.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when docker-compose.yml uses npm command override instead of bun
- **Property (P)**: The desired behavior when the frontend service starts - it should use bun commands that match the container's runtime
- **Preservation**: Existing docker-compose.dev.yml behavior, Containerfile configuration, volume mounts, environment variables, and port mappings that must remain unchanged
- **frontend service**: The service definition in `infrastructure/docker/docker-compose.yml` that runs the Lit 3 web application
- **command override**: The Docker Compose `command:` directive that overrides the Containerfile's default CMD
- **Bun runtime**: The JavaScript runtime (oven/bun:1) used as the base image in frontend/Containerfile

## Bug Details

### Fault Condition

The bug manifests when the frontend service is started using the production docker-compose.yml configuration. The service definition includes a `command: npm run dev` override that attempts to execute npm commands in a container built from the Bun runtime image, where npm is not installed.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type DockerComposeServiceConfig
  OUTPUT: boolean
  
  RETURN input.service_name == "frontend"
         AND input.file_path == "infrastructure/docker/docker-compose.yml"
         AND input.command_override == "npm run dev"
         AND input.base_image == "oven/bun:1"
END FUNCTION
```

### Examples

- **Production startup failure**: Starting frontend service with `docker-compose up frontend` results in error "npm: command not found" because the Bun container doesn't include npm
- **Development vs production mismatch**: docker-compose.dev.yml works correctly (uses Containerfile default), but docker-compose.yml fails due to npm override
- **Build vs runtime inconsistency**: Containerfile successfully builds with `bun install` and defines `CMD ["bun", "run", "dev"]`, but docker-compose.yml overrides this with incompatible npm command
- **Edge case - command override removal**: If the command override line is removed entirely, the service would work correctly using the Containerfile's default CMD

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- docker-compose.dev.yml must continue to use the default CMD from Containerfile (no command override)
- frontend Containerfile must continue to use `oven/bun:1` as the base image
- frontend service must continue to expose port 3000 and map to ${PORT_FRONTEND:-28030}
- Volume mounts must continue to mount `./frontend:/app` and `/app/node_modules`
- Environment variables VITE_API_URL and VITE_WS_URL must continue to be passed to the container
- Service dependencies and healthcheck configuration must remain unchanged

**Scope:**
All configuration in docker-compose.yml that does NOT involve the frontend service's command override should be completely unaffected by this fix. This includes:
- All other service definitions (django, nginx, postgres, redis, vault, clickhouse)
- Network configuration and service dependencies
- Volume definitions and mount points
- Environment variable definitions
- Port mappings and healthcheck configurations

## Hypothesized Root Cause

Based on the bug description and file analysis, the most likely issue is:

1. **Copy-Paste Error from npm-based Configuration**: The docker-compose.yml was likely created or updated when the project used npm, and the command override was not updated when the frontend was migrated to Bun
   - The Containerfile clearly uses Bun (`oven/bun:1`, `bun install`, `CMD ["bun", "run", "dev"]`)
   - The docker-compose.yml still references npm in the command override
   - This suggests the compose file was not updated during the Bun migration

2. **Inconsistent Configuration Management**: The development compose file (docker-compose.dev.yml) doesn't have a command override and works correctly, while the production compose file has the incorrect npm override

3. **Missing Validation**: There was no validation step to ensure the command override matches the container's available runtime

## Correctness Properties

Property 1: Fault Condition - Frontend Service Uses Bun Commands

_For any_ Docker Compose configuration where the frontend service is defined with a command override in infrastructure/docker/docker-compose.yml, the fixed configuration SHALL use `bun run dev` instead of `npm run dev`, ensuring the command matches the Bun runtime installed in the container.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation - Non-Frontend Configuration Unchanged

_For any_ Docker Compose configuration element that is NOT the frontend service's command override (other services, volumes, networks, environment variables, port mappings), the fixed docker-compose.yml SHALL produce exactly the same configuration as the original file, preserving all existing infrastructure setup.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `infrastructure/docker/docker-compose.yml`

**Section**: Frontend service definition (line 166)

**Specific Changes**:
1. **Command Override Update**: Change the command from npm to bun
   - Current: `command: npm run dev`
   - Fixed: `command: bun run dev`

2. **Verification**: Ensure the command matches the Containerfile's CMD format
   - Containerfile uses: `CMD ["bun", "run", "dev"]`
   - Compose override should use: `command: bun run dev` (string format is equivalent)

3. **No Other Changes Required**: All other frontend service configuration remains unchanged
   - Build context: `../../frontend`
   - Container name: `gpubroker_frontend`
   - Environment variables: VITE_API_URL, VITE_WS_URL
   - Port mapping: `${PORT_FRONTEND:-28030}:3000`
   - Volume mounts: `./frontend:/app` and `/app/node_modules`

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code (npm command fails in Bun container), then verify the fix works correctly (bun command succeeds) and preserves existing behavior (all other services and configurations unchanged).

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that the npm command override fails in the Bun-based container.

**Test Plan**: Attempt to start the frontend service using the UNFIXED docker-compose.yml and observe the failure when npm commands are executed in a Bun-only container. Document the exact error message and failure mode.

**Test Cases**:
1. **Frontend Service Startup Test**: Run `docker-compose -f infrastructure/docker/docker-compose.yml up frontend` (will fail on unfixed code with "npm: command not found")
2. **Container Runtime Verification**: Exec into the running container and verify npm is not available but bun is (will confirm root cause)
3. **Containerfile Default Test**: Build and run the container without compose override to verify it works with default CMD (will succeed, proving the Containerfile is correct)
4. **Dev Compose Comparison**: Run docker-compose.dev.yml to verify it works without command override (will succeed, proving the issue is specific to the production compose file)

**Expected Counterexamples**:
- Frontend service fails to start with error message containing "npm: command not found" or similar
- Container logs show command execution failure immediately after startup
- Possible causes: npm not installed in oven/bun:1 image, incorrect command override in compose file

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (frontend service with npm command override), the fixed configuration produces the expected behavior (successful startup with bun command).

**Pseudocode:**
```
FOR ALL config WHERE isBugCondition(config) DO
  result := startFrontendService_fixed(config)
  ASSERT result.status == "running"
  ASSERT result.command_executed == "bun run dev"
  ASSERT result.container_logs_contain("Vite dev server started")
END FOR
```

### Preservation Checking

**Goal**: Verify that for all configuration elements where the bug condition does NOT hold (all non-frontend-command configuration), the fixed docker-compose.yml produces the same result as the original file.

**Pseudocode:**
```
FOR ALL config_element WHERE NOT isBugCondition(config_element) DO
  ASSERT docker_compose_original[config_element] = docker_compose_fixed[config_element]
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It can verify all service definitions remain unchanged (django, nginx, postgres, redis, vault, clickhouse)
- It catches any unintended modifications to volumes, networks, or environment variables
- It provides strong guarantees that only the specific command override was changed

**Test Plan**: Parse both the unfixed and fixed docker-compose.yml files, then compare all configuration elements except the frontend service's command field.

**Test Cases**:
1. **Service Definitions Preservation**: Verify all other services (django, nginx, postgres, redis, vault, clickhouse) have identical configuration
2. **Volume Definitions Preservation**: Verify all volume definitions remain unchanged
3. **Environment Variables Preservation**: Verify all environment variable definitions for all services remain unchanged
4. **Port Mappings Preservation**: Verify all port mappings remain unchanged
5. **Frontend Service Non-Command Fields**: Verify frontend service's build context, container name, environment, ports, and volumes remain unchanged

### Unit Tests

- Test that docker-compose.yml parses correctly after the fix
- Test that the frontend service definition contains `command: bun run dev`
- Test that all other service definitions remain unchanged
- Test that the fixed compose file is valid YAML

### Property-Based Tests

- Generate random service names and verify their configuration is unchanged between original and fixed files
- Generate random configuration paths (e.g., services.django.environment.DEBUG) and verify they are identical
- Test that only the specific path `services.frontend.command` has changed from "npm run dev" to "bun run dev"

### Integration Tests

- Test full stack startup with fixed docker-compose.yml to verify all services start correctly
- Test frontend service accessibility on port 28030 after startup
- Test that Vite dev server is running and serving the application
- Test that environment variables (VITE_API_URL, VITE_WS_URL) are correctly passed to the frontend
- Test that volume mounts work correctly (hot reload on file changes)
