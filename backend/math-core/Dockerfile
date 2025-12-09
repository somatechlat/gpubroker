# ============================================
# GPUMathBroker - MASTER DATA ANALYSIS ENGINE
# Enterprise-Grade Mathematical & Statistical Toolkit
# ============================================
# ⚠️ WARNING: REAL IMPLEMENTATION ONLY ⚠️
# We do NOT mock, bypass, or invent data.
# ============================================

FROM python:3.11-slim-bookworm

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies including R and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials
    build-essential \
    gcc \
    g++ \
    gfortran \
    cmake \
    pkg-config \
    # R and dependencies
    r-base \
    r-base-dev \
    # Libraries for scientific computing
    libopenblas-dev \
    liblapack-dev \
    libblas-dev \
    # Libraries for data processing
    libhdf5-dev \
    libffi-dev \
    # Libraries for R packages
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    libfontconfig1-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libfreetype6-dev \
    libpng-dev \
    libtiff5-dev \
    libjpeg-dev \
    # Utilities
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install R packages for statistical analysis
RUN R -e "install.packages(c( \
    'jsonlite', \
    'dplyr', \
    'tidyr', \
    'ggplot2', \
    'forecast', \
    'tseries', \
    'zoo', \
    'xts', \
    'anomalize', \
    'tibbletime', \
    'timetk', \
    'modeltime', \
    'tidymodels', \
    'ranger', \
    'glmnet', \
    'caret', \
    'e1071', \
    'randomForest', \
    'xgboost', \
    'lightgbm', \
    'Metrics', \
    'MLmetrics' \
    ), repos='https://cloud.r-project.org/', Ncpus=4)"

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies in stages for better caching
# Stage 1: Core scientific computing
RUN pip install --no-cache-dir \
    numpy==1.26.3 \
    scipy==1.12.0 \
    pandas==2.1.4 \
    polars==0.20.6

# Stage 2: ML frameworks
RUN pip install --no-cache-dir \
    scikit-learn==1.4.0 \
    xgboost==2.0.3 \
    lightgbm==4.3.0

# Stage 3: PyTorch (CPU version for smaller image)
RUN pip install --no-cache-dir \
    torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu

# Stage 4: Remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 mathcore && chown -R mathcore:mathcore /app
USER mathcore

# Expose port
EXPOSE 8004

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8004/health').raise_for_status()"

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004", "--workers", "4"]
