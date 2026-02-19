# Bugfix Requirements Document

## Introduction

The frontend build process is incorrectly configured to use npm commands in the production Docker Compose configuration, despite the project being standardized on Bun as the package manager. This causes build failures and inconsistency between development and production environments. The frontend Containerfile correctly uses Bun (`oven/bun:1` image with `bun install` and `bun run dev`), but the production docker-compose.yml overrides this with `npm run dev`, creating a mismatch.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the frontend service is started using docker-compose.yml THEN the system executes `npm run dev` command override

1.2 WHEN the frontend container attempts to run npm commands THEN the system fails because npm is not installed in the Bun-based container image

1.3 WHEN developers use production docker-compose.yml THEN the system creates inconsistency with the Containerfile's intended Bun-based execution

### Expected Behavior (Correct)

2.1 WHEN the frontend service is started using docker-compose.yml THEN the system SHALL use `bun run dev` command instead of npm

2.2 WHEN the frontend container starts THEN the system SHALL execute commands using the Bun runtime that is installed in the container

2.3 WHEN developers use production docker-compose.yml THEN the system SHALL maintain consistency with the Containerfile's Bun-based configuration

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the frontend service is started using docker-compose.dev.yml THEN the system SHALL CONTINUE TO use the default CMD from Containerfile (no command override)

3.2 WHEN the frontend Containerfile is built THEN the system SHALL CONTINUE TO use `oven/bun:1` as the base image

3.3 WHEN the frontend container installs dependencies THEN the system SHALL CONTINUE TO use `bun install` command

3.4 WHEN the frontend service exposes ports THEN the system SHALL CONTINUE TO expose port 3000

3.5 WHEN the frontend service mounts volumes THEN the system SHALL CONTINUE TO mount the frontend directory and node_modules

3.6 WHEN environment variables are passed to frontend THEN the system SHALL CONTINUE TO receive VITE_API_URL and VITE_WS_URL configurations
