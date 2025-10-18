#!/usr/bin/env python3
import asyncio
from sqlalchemy import create_engine, text
from app.core.config import settings

def check_mappings():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT pm.id, pm.external_product_id, pm.external_variant_id, es.external_id as shop_id 
            FROM product_mappings pm 
            JOIN external_systems es ON pm.external_system_id = es.id 
            WHERE es.system_type = 'PRINTIFY' 
            AND pm.tenant_id = 1
        """))
        mappings = result.fetchall()
        print("Printify产品映射:")
        for mapping in mappings:
            print(f'ID: {mapping[0]}, Product: {mapping[1]}, Variant: {mapping[2]}, Shop: {mapping[3]}')

if __name__ == "__main__":
    check_mappings()
