#!/bin/bash
# Stop development environment

echo "🛑 Stopping SupplyNexus Fulfillment Service Development Environment"

docker-compose -f docker-compose.dev.yml down

echo "✅ Development environment stopped!"
