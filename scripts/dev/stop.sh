#!/bin/bash
# Stop dev environment

echo "🛑 Stopping SupplyNexus Fulfillment Service Dev Environment"

docker-compose -f docker-compose.dev.yml down

echo "✅ Dev environment stopped!"
