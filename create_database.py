#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
import os
from datetime import datetime

class CustomerOrdersDatabase:
    def __init__(self, db_name='customer_orders.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        
    def create_connection(self):
        """إنشاء اتصال بقاعدة البيانات"""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            print(f"✅ تم الاتصال بقاعدة البيانات: {self.db_name}")
            return True
        except Exception as e:
            print(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
            return False
    
    def create_tables(self):
        """إنشاء الجداول المطلوبة"""
        try:
            # جدول العملاء
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول الطلبات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    wasl_number TEXT,
                    order_number TEXT,
                    customer_name TEXT,
                    mandob_name TEXT,
                    city TEXT,
                    area TEXT,
                    customer_phone TEXT,
                    total_amount REAL,
                    delivery_fee REAL,
                    net_amount REAL,
                    status TEXT,
                    add_date TEXT,
                    print_date TEXT,
                    added_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers (id)
                )
            ''')
            
            # جدول فترات البحث
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_periods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_date TEXT,
                    end_date TEXT,
                    total_orders INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول الطلبات المعالجة
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wasl_number TEXT UNIQUE,
                    processed_at TEXT,
                    processed_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.conn.commit()
            print("✅ تم إنشاء الجداول بنجاح")
            return True
            
        except Exception as e:
            print(f"❌ خطأ في إنشاء الجداول: {e}")
            return False
    
    def insert_customers(self, customers_data):
        """إدراج العملاء"""
        try:
            for customer in customers_data:
                self.cursor.execute('''
                    INSERT OR REPLACE INTO customers (id, name)
                    VALUES (?, ?)
                ''', (customer['id'], customer['name']))
            
            self.conn.commit()
            print(f"✅ تم إدراج {len(customers_data)} عميل")
            return True
            
        except Exception as e:
            print(f"❌ خطأ في إدراج العملاء: {e}")
            return False
    
    def insert_orders(self, orders_data, period_data):
        """إدراج الطلبات"""
        try:
            # إدراج فترة البحث
            self.cursor.execute('''
                INSERT INTO search_periods (start_date, end_date, total_orders)
                VALUES (?, ?, ?)
            ''', (period_data['start'], period_data['end'], orders_data['total_orders']))
            
            period_id = self.cursor.lastrowid
            
            orders_count = 0
            for customer_result in orders_data['results']:
                customer_id = customer_result['customer_id']
                
                for order in customer_result['orders']:
                    # تحويل المبالغ إلى أرقام
                    total_amount = float(order['total_amount']) if order['total_amount'] and order['total_amount'] != '0' else 0.0
                    delivery_fee = float(order['delivery_fee']) if order['delivery_fee'] and order['delivery_fee'] != '0' else 0.0
                    net_amount = float(order['net_amount']) if order['net_amount'] and order['net_amount'] != '0' else 0.0
                    
                    self.cursor.execute('''
                        INSERT INTO orders (
                            customer_id, wasl_number, order_number, customer_name,
                            mandob_name, city, area, customer_phone,
                            total_amount, delivery_fee, net_amount, status,
                            add_date, print_date, added_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        customer_id,
                        order['wasl_number'],
                        order['order_number'],
                        order['customer_name'],
                        order['mandob_name'],
                        order['city'],
                        order['area'],
                        order['customer_phone'],
                        total_amount,
                        delivery_fee,
                        net_amount,
                        order['status'],
                        order['add_date'],
                        order['print_date'],
                        order['added_by']
                    ))
                    orders_count += 1
            
            self.conn.commit()
            print(f"✅ تم إدراج {orders_count} طلب")
            return True
            
        except Exception as e:
            print(f"❌ خطأ في إدراج الطلبات: {e}")
            return False
    
    def create_indexes(self):
        """إنشاء فهارس لتحسين الأداء"""
        try:
            # فهرس على رقم الوصل
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_wasl_number ON orders (wasl_number)')
            
            # فهرس على رقم الطلب
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_number ON orders (order_number)')
            
            # فهرس على معرف العميل
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_customer_id ON orders (customer_id)')
            
            # فهرس على التاريخ
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_add_date ON orders (add_date)')
            
            # فهرس على الحالة
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON orders (status)')
            
            # فهرس على رقم الوصل في الطلبات المعالجة
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_processed_wasl_number ON processed_orders (wasl_number)')
            
            self.conn.commit()
            print("✅ تم إنشاء الفهارس بنجاح")
            return True
            
        except Exception as e:
            print(f"❌ خطأ في إنشاء الفهارس: {e}")
            return False
    
    def get_statistics(self):
        """الحصول على إحصائيات قاعدة البيانات"""
        try:
            # عدد العملاء
            self.cursor.execute('SELECT COUNT(*) FROM customers')
            customers_count = self.cursor.fetchone()[0]
            
            # عدد الطلبات
            self.cursor.execute('SELECT COUNT(*) FROM orders')
            orders_count = self.cursor.fetchone()[0]
            
            # إجمالي المبالغ
            self.cursor.execute('SELECT SUM(total_amount), SUM(delivery_fee), SUM(net_amount) FROM orders')
            amounts = self.cursor.fetchone()
            total_amount = amounts[0] or 0
            total_delivery = amounts[1] or 0
            total_net = amounts[2] or 0
            
            # عدد الطلبات لكل عميل
            self.cursor.execute('''
                SELECT c.name, COUNT(o.id) as orders_count
                FROM customers c
                LEFT JOIN orders o ON c.id = o.customer_id
                GROUP BY c.id, c.name
                ORDER BY orders_count DESC
            ''')
            customer_stats = self.cursor.fetchall()
            
            print("\n📊 إحصائيات قاعدة البيانات:")
            print("=" * 40)
            print(f"👥 عدد العملاء: {customers_count}")
            print(f"📦 عدد الطلبات: {orders_count}")
            print(f"💰 إجمالي المبالغ: {total_amount:,.2f}")
            print(f"🚚 إجمالي رسوم التوصيل: {total_delivery:,.2f}")
            print(f"💵 إجمالي الصافي: {total_net:,.2f}")
            
            print("\n📋 إحصائيات العملاء:")
            for customer_name, orders_count in customer_stats:
                print(f"  • {customer_name}: {orders_count} طلب")
            
            return {
                'customers_count': customers_count,
                'orders_count': orders_count,
                'total_amount': total_amount,
                'total_delivery': total_delivery,
                'total_net': total_net,
                'customer_stats': customer_stats
            }
            
        except Exception as e:
            print(f"❌ خطأ في الحصول على الإحصائيات: {e}")
            return None
    
    def close_connection(self):
        """إغلاق الاتصال"""
        if self.conn:
            self.conn.close()
            print("✅ تم إغلاق الاتصال بقاعدة البيانات")

def main():
    # قائمة العملاء
    customers = [
        {'id': 185, 'name': 'سبونجي'},
        {'id': 186, 'name': 'العاب ريمي'},
        {'id': 187, 'name': 'ويني'},
        {'id': 188, 'name': 'كاتي'},
        {'id': 189, 'name': 'بندق'},
        {'id': 190, 'name': 'مشمش'},
        {'id': 191, 'name': 'مشمش2'},
        {'id': 192, 'name': 'العاب ماريو'},
        {'id': 194, 'name': 'سابوي'}
    ]
    
    # إنشاء قاعدة البيانات
    db = CustomerOrdersDatabase()
    
    if db.create_connection():
        # إنشاء الجداول
        if db.create_tables():
            # إدراج العملاء
            db.insert_customers(customers)
            
            # قراءة ملف JSON
            json_file = 'all_customers_orders_07-10-2025.json'
            if os.path.exists(json_file):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # إدراج الطلبات
                db.insert_orders(data, data['period'])
                
                # إنشاء الفهارس
                db.create_indexes()
                
                # عرض الإحصائيات
                db.get_statistics()
                
                print(f"\n✅ تم إنشاء قاعدة البيانات بنجاح: {db.db_name}")
            else:
                print(f"❌ ملف JSON غير موجود: {json_file}")
        
        db.close_connection()

if __name__ == "__main__":
    main() 