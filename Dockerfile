# Production-Grade Hugging Face Spaces Dockerfile
# Hosting Hermes-Notebook RAG + Antigravity CLI for FREE on Hugging Face (16GB RAM)

FROM python:3.11-slim

# Install system dependencies & curl for Ollama
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama client for local LLM sidecar execution
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set working directory
WORKDIR /app

# Copy requirements and package files
COPY pyproject.toml /app/
COPY antigravity /app/antigravity

# Install Python dependencies and local CLI package
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Create persistent dataset / vector store mount directory
RUN mkdir -p /app/vector_store && chmod -R 777 /app/vector_store

# Set environment variables for Hugging Face Spaces
ENV PORT=7860
ENV VECTOR_DB_PATH=/app/vector_store
ENV OLLAMA_HOST=127.0.0.1:11434

# Startup script to start Ollama in background and launch CLI server
RUN echo '#!/bin/bash\n\
ollama serve &\n\
sleep 5\n\
echo "Pulling Hermes-3 model..."\n\
ollama pull hermes3 || true\n\
python -m antigravity.cli status\n\
echo "Antigravity CLI Ready on HF Spaces."\n\
tail -f /dev/null\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 7860

ENTRYPOINT ["/app/entrypoint.sh"]
