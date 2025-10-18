#!/bin/bash
# Health check script for MCP-DDS Gateway

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

GATEWAY_HOST="${GATEWAY_HOST:-localhost}"
GATEWAY_PORT="${GATEWAY_PORT:-9090}"

echo "MCP-DDS Gateway Health Check"
echo "=============================="
echo "Host: $GATEWAY_HOST"
echo "Port: $GATEWAY_PORT"
echo ""

# Check liveness
echo -n "Checking liveness... "
if curl -sf "http://${GATEWAY_HOST}:${GATEWAY_PORT}/health" > /dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    exit 1
fi

# Check readiness
echo -n "Checking readiness... "
if curl -sf "http://${GATEWAY_HOST}:${GATEWAY_PORT}/ready" > /dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    exit 1
fi

# Check metrics endpoint
echo -n "Checking metrics... "
if curl -sf "http://${GATEWAY_HOST}:${GATEWAY_PORT}/metrics" > /dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}All health checks passed!${NC}"
