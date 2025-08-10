#!/bin/bash

# Database setup script for SupplyNexus Fulfillment Service
set -e

echo "🚀 Setting up database for SupplyNexus Fulfillment Service..."

# Change to backend directory
cd backend

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  Virtual environment not found. Please activate it manually."
fi

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://supplynexus_admin:aabbccdd@localhost:5433/supplynexus"
export DATABASE_URL_SYNC="postgresql://supplynexus_admin:aabbccdd@localhost:5433/supplynexus"

echo "🔧 Environment variables set:"
echo "   DATABASE_URL: $DATABASE_URL"
echo "   DATABASE_URL_SYNC: $DATABASE_URL_SYNC"

# Check if database is accessible
echo "🔍 Testing database connection..."
python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        port=5433,
        database='supplynexus',
        user='supplynexus_admin',
        password='aabbccdd'
    )
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

# Generate initial migration
echo "📝 Generating initial migration..."
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
echo "🔄 Applying migrations to database..."
alembic upgrade head

# Check current migration status
echo "📊 Current migration status:"
alembic current

echo "✅ Database setup completed successfully!"
echo ""
echo "📋 Summary:"
echo "   - Database tables created"
echo "   - Migration applied"
echo "   - Ready for development"
