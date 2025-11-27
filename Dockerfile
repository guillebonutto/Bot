# Stage 1: Builder (Build Rust extension for Linux)
FROM python:3.11 as builder

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install maturin and patchelf (required for linux builds)
RUN pip install maturin patchelf

# Copy library source
COPY BinaryOptionsTools-v2 /app/BinaryOptionsTools-v2

# Build wheel
WORKDIR /app/BinaryOptionsTools-v2/BinaryOptionsToolsV2
RUN maturin build --release --out dist

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy built wheel from builder and install
COPY --from=builder /app/BinaryOptionsTools-v2/BinaryOptionsToolsV2/dist/*.whl .
RUN pip install *.whl

# Copy app code
COPY . .

# Run bot
CMD ["python", "main.py"]
