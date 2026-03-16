FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY proxy/ ./proxy/

# Create non-root user
RUN useradd -m -u 1000 proxyuser && chown -R proxyuser:proxyuser /app
USER proxyuser

# Expose port
EXPOSE 1080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s = socket.socket(); s.connect(('127.0.0.1', 1080)); s.close()" || exit 1

# Run
CMD ["python", "-m", "proxy.main"]
