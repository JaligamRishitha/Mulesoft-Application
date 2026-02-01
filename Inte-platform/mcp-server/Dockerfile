FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the MCP server file
COPY mcp_mulesoft.py .

EXPOSE 8090

CMD ["python", "mcp_mulesoft.py"]
