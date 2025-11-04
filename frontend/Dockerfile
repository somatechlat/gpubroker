# ⚠️ WARNING: REAL IMPLEMENTATION ONLY ⚠️
# We do NOT mock, bypass, or invent data.
# We use ONLY real servers, real APIs, and real data.

FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
