FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy all application files first
COPY . .

# Create venv and install dependencies at build time
RUN uv venv --python 3.12 && uv sync --no-dev

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Run migrations before starting the app
ENTRYPOINT ["./docker-entrypoint.sh"]
