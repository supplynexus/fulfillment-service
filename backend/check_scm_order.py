#!/usr/bin/env python3
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 创建数据库连接
engine = create_engine('postgresql://supplynexus:supplynexus@localhost:5432/supplynexus_dev')
Session = sessionmaker(bind=engine)
session = Session()

try:
    # 查询 SCM 订单 #59 的 line_items
    result = session.execute(text('SELECT id, line_items FROM scm_orders WHERE id = 59'))
    row = result.fetchone()
    if row:
        print('SCM Order ID:', row[0])
        print('Line Items:', json.dumps(row[1], indent=2, ensure_ascii=False))
    else:
        print('SCM Order #59 not found')
        
    # 查询源订单信息
    result = session.execute(text('''
        SELECT o.id, o.order_number, o.external_order_number, o.external_order_name, o.line_items
        FROM orders o
        JOIN scm_order_sources sos ON o.id = sos.source_order_id
        WHERE sos.scm_order_id = 59
    '''))
    source_orders = result.fetchall()
    print('\nSource Orders:')
    for order in source_orders:
        print('Order ID:', order[0], 'Order Number:', order[1], 'External:', order[2], 'Name:', order[3])
        print('Line Items:', json.dumps(order[4], indent=2, ensure_ascii=False))
        
finally:
    session.close()







