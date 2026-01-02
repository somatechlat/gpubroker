# ⚠️ WARNING: REAL IMPLEMENTATION ONLY ⚠️
# We do NOT mock, bypass, or invent data.
# We use ONLY real servers, real APIs, and real data.

FROM oven/bun:1 AS builder

WORKDIR /app

# Install dependencies with Bun
COPY package*.json bun.lock* ./
RUN bun install --frozen-lockfile || bun install

# Copy source code
COPY . .

# Create public folder if it doesn't exist (to avoid COPY error)
RUN mkdir -p public

# Build the application with Bun
RUN bun run build

# Production stage
FROM oven/bun:1-slim

WORKDIR /app

# Copy built assets
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Expose port
EXPOSE 3000

# Start the application with Bun
CMD ["bun", "run", "start"]
