FROM python:3.12-alpine
WORKDIR /app
COPY mcp-server/pyproject.toml mcp-server/README.md ./
COPY mcp-server/coneshare_mcp ./coneshare_mcp
RUN pip install --no-cache-dir .
ENV MCP_HOST=0.0.0.0 MCP_PORT=8001 MCP_PATH=/mcp/ CONESHARE_URL=http://web
CMD ["coneshare-mcp"]
