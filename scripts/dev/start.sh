#!/bin/bash
# Start dev environment

echo "🚀 Starting SupplyNexus Fulfillment Service Dev Environment"

docker-compose -f docker-compose.dev.yml up -d

echo "✅ Dev environment started!"
echo ""
echo "Services available at:"
echo "  📊 Backend API:        http://localhost:8000"
echo "  📊 API Documentation:  http://localhost:8000/api/v1/docs"
echo "  🖥️  Frontend:          http://localhost:3000"
echo "  🌸 Flower (Celery):    http://localhost:5555"
