FROM python:3.13-slim

WORKDIR /app

# Install uv (astral's high-performance python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the dependency files first to cache them
COPY pyproject.toml uv.lock ./

# Copy the rest of the application files before running uv sync 
# (uv sync tries to install the local package, so the source must be present)
COPY src/ ./src/
COPY main.py ./
COPY README.md ./

# Install the dependencies in frozen mode to ensure reproducibility
RUN uv sync --frozen

# Expose the API port
EXPOSE 8000

# Set Python to unbuffered mode to ensure logs are streamed immediately
ENV PYTHONUNBUFFERED=1

# Start the FastAPI server using uvicorn via uv
ENTRYPOINT ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
