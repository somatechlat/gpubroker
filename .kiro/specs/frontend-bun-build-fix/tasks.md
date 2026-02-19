# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Fault Condition** - Frontend Service npm Command Fails in Bun Container
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to the concrete failing case: frontend service with npm command override in docker-compose.yml
  - Test that frontend service with `command: npm run dev` fails to start in Bun container (from Fault Condition in design)
  - The test assertions should verify that after fix, the service uses `bun run dev` and starts successfully
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found: "npm: command not found" error, service fails to start
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-Frontend Configuration Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED docker-compose.yml for all non-frontend-command configuration
  - Parse the UNFIXED docker-compose.yml and record all service definitions, volumes, networks, environment variables
  - Write property-based tests capturing that all configuration elements except `services.frontend.command` remain identical
  - Property-based testing generates many test cases for stronger guarantees (test all services, all env vars, all volumes)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 3. Fix frontend service command override in docker-compose.yml

  - [x] 3.1 Implement the fix
    - Change command from `npm run dev` to `bun run dev` in infrastructure/docker/docker-compose.yml line 166
    - Verify the command matches the Containerfile's CMD format: `CMD ["bun", "run", "dev"]`
    - Ensure no other changes to frontend service configuration (build context, container name, environment, ports, volumes)
    - _Bug_Condition: isBugCondition(input) where input.service_name == "frontend" AND input.command_override == "npm run dev" AND input.base_image == "oven/bun:1"_
    - _Expected_Behavior: Frontend service uses `command: bun run dev`, starts successfully, and Vite dev server runs_
    - _Preservation: All other docker-compose.yml configuration (other services, volumes, networks, environment variables, port mappings) remains unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Frontend Service Starts with Bun Command
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Frontend Configuration Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
