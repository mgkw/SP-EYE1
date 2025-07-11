#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import json
from datetime import datetime
import sys

class OrderMonitor:
    def __init__(self, session_id):
        self.session_id = session_id
        self.base_url = 'https://alkarar-exp.com/'
        
        # إعداد الجلسة مع تحسينات للسرعة
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        # تحسين إعدادات الجلسة للسرعة
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # إضافة أكواد الجلسة في قائمة الإعدادات
        self.session.cookies.set('PHPSESSID', session_id, domain='alkarar-exp.com')
        
        # إضافة ملفات تعريف الارتباط الإضافية للسرعة
        self.session.cookies.set('session_active', 'true', domain='alkarar-exp.com')
        self.session.cookies.set('last_activity', str(int(time.time())), domain='alkarar-exp.com')
        
        # ضبط إعدادات الجلسة للأداء الأمثل
        self.session.trust_env = False
        self.session.max_redirects = 5
        
        # إضافة Headers إضافية للسرعة
        self.session.headers.update({
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-CH-UA': '"Google Chrome";v="137", "Chromium";v="137", "Not:A-Brand";v="24"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"Windows"',
            'DNT': '1',
            'Priority': 'u=0, i'
        })
        
        # قائمة العملاء
        self.customers = [
            {'id': 185, 'name': 'سبونجي'},
            {'id': 186, 'name': 'العاب ريمي'},
            {'id': 187, 'name': 'ويني'},
            {'id': 188, 'name': 'كاتي'},
            {'id': 189, 'name': 'بندق'},
            {'id': 190, 'name': 'مشمش'},
            {'id': 191, 'name': 'مشمش2'},
            {'id': 192, 'name': 'العاب ماريو'},
            {'id': 194, 'name': 'سابوي'},
            {'id': 248, 'name': 'العاب نيلزز'},
            {'id': 225, 'name': 'العاب زيتونة'},
            {'id': 203, 'name': 'بطريق'},
        ]
        
        # قاعدة البيانات
        self.db_name = 'customer_orders.db'
        self.conn = None
        self.cursor = None
        
        # متغيرات للتحسين
        self.last_customer_check = {}  # تخزين آخر فحص لكل عميل
        self.customer_rotation = 0  # دوران العملاء للتوزيع
    
    def create_connection(self):
        """إنشاء اتصال محسّن بقاعدة البيانات مع منع الحفظ المكرر"""
        try:
            # إعدادات محسنة لقاعدة البيانات
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.conn.execute("PRAGMA synchronous = OFF")
            self.conn.execute("PRAGMA journal_mode = MEMORY")
            self.conn.execute("PRAGMA cache_size = 10000")
            self.conn.execute("PRAGMA temp_store = MEMORY")
            self.conn.execute("PRAGMA mmap_size = 268435456")  # 256MB
            
            self.cursor = self.conn.cursor()
            
            # إنشاء جدول للمراقبة مع منع التكرار
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_monitoring (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wasl_number TEXT NOT NULL,
                    order_number TEXT NOT NULL,
                    customer_id INTEGER,
                    customer_name TEXT,
                    old_total_amount REAL,
                    new_total_amount REAL,
                    old_status TEXT,
                    new_status TEXT,
                    change_type TEXT,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    customer_phone TEXT,
                    city TEXT,
                    area TEXT,
                    UNIQUE(wasl_number, order_number, change_type, detected_at),
                    FOREIGN KEY (customer_id) REFERENCES customers (id)
                )
            ''')
            
            # إنشاء جدول للطلبات المعزولة مع منع التكرار
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS isolated_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wasl_number TEXT NOT NULL,
                    order_number TEXT NOT NULL,
                    customer_id INTEGER,
                    customer_name TEXT,
                    total_amount REAL,
                    status TEXT,
                    isolated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reason TEXT,
                    customer_phone TEXT,
                    city TEXT,
                    area TEXT,
                    UNIQUE(wasl_number, order_number, reason),
                    FOREIGN KEY (customer_id) REFERENCES customers (id)
                )
            ''')
            
            # إنشاء جدول للطلبات المعالجة مع منع التكرار
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wasl_number TEXT UNIQUE NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_by TEXT DEFAULT 'system'
                )
            ''')
            
            # التحقق من وجود جدول الطلبات وإضافة unique constraint إذا لزم الأمر
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders_unique_check (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wasl_number TEXT NOT NULL,
                    order_number TEXT NOT NULL,
                    customer_id INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(wasl_number, order_number, customer_id)
                )
            ''')
            
            # إنشاء فهارس للسرعة
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_orders_wasl_number 
                ON orders(wasl_number)
            ''')
            
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_orders_customer_id 
                ON orders(customer_id)
            ''')
            
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_orders_add_date 
                ON orders(add_date)
            ''')
            
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_monitoring_wasl_number 
                ON order_monitoring(wasl_number)
            ''')
            
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_monitoring_detected_at 
                ON order_monitoring(detected_at)
            ''')
            
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_isolated_wasl_number 
                ON isolated_orders(wasl_number)
            ''')
            
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_isolated_isolated_at 
                ON isolated_orders(isolated_at)
            ''')
            
            self.conn.commit()
            print(f"✅ تم الاتصال المحسن بقاعدة البيانات مع منع التكرار: {self.db_name}")
            return True
        except Exception as e:
            print(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
            return False
    
    def get_existing_orders(self):
        """الحصول على الطلبات الموجودة في قاعدة البيانات مع التحقق من التفرد"""
        try:
            # استعلام محسن لتجنب الطلبات المكررة
            self.cursor.execute('''
                SELECT DISTINCT o.wasl_number, o.order_number, o.customer_id, o.customer_name, 
                       o.total_amount, o.status
                FROM orders o
                INNER JOIN orders_unique_check ouc ON (
                    o.wasl_number = ouc.wasl_number AND 
                    o.order_number = ouc.order_number AND 
                    o.customer_id = ouc.customer_id
                )
                ORDER BY o.id DESC
            ''')
            
            existing_orders = {}
            for row in self.cursor.fetchall():
                wasl_number, order_number, customer_id, customer_name, total_amount, status = row
                # استخدام مفتاح مركب من رقم الوصل ورقم الطلب
                key = f"{wasl_number}_{order_number}"
                existing_orders[key] = {
                    'wasl_number': wasl_number,
                    'order_number': order_number,
                    'customer_id': customer_id,
                    'customer_name': customer_name,
                    'total_amount': total_amount,
                    'status': status
                }
            
            return existing_orders
        except Exception as e:
            print(f"❌ خطأ في الحصول على الطلبات الموجودة: {e}")
            # العودة للطريقة القديمة في حالة الخطأ
            try:
                self.cursor.execute('''
                    SELECT wasl_number, order_number, customer_id, customer_name, 
                           total_amount, status
                    FROM orders
                    ORDER BY id DESC
                ''')
                existing_orders = {}
                for row in self.cursor.fetchall():
                    wasl_number, order_number, customer_id, customer_name, total_amount, status = row
                    key = f"{wasl_number}_{order_number}"
                    existing_orders[key] = {
                        'wasl_number': wasl_number,
                        'order_number': order_number,
                        'customer_id': customer_id,
                        'customer_name': customer_name,
                        'total_amount': total_amount,
                        'status': status
                    }
                return existing_orders
            except Exception as e2:
                print(f"❌ خطأ في الطريقة البديلة: {e2}")
                return {}

    def clean_duplicate_data(self):
        """تنظيف البيانات المكررة القديمة"""
        try:
            print("🧹 بدء تنظيف البيانات المكررة...")
            
            # تنظيف التغييرات المكررة في المراقبة (الاحتفاظ بالأحدث)
            self.cursor.execute('''
                DELETE FROM order_monitoring 
                WHERE id NOT IN (
                    SELECT MAX(id) 
                    FROM order_monitoring 
                    GROUP BY wasl_number, order_number, change_type, 
                             old_total_amount, new_total_amount, old_status, new_status
                )
            ''')
            
            # تنظيف الطلبات المعزولة المكررة (الاحتفاظ بالأحدث)
            self.cursor.execute('''
                DELETE FROM isolated_orders 
                WHERE id NOT IN (
                    SELECT MAX(id) 
                    FROM isolated_orders 
                    GROUP BY wasl_number, order_number, reason
                )
            ''')
            
            # تنظيف البيانات القديمة من جدول المراقبة (أكثر من 30 يوم)
            self.cursor.execute('''
                DELETE FROM order_monitoring 
                WHERE datetime(detected_at) < datetime('now', '-30 days')
            ''')
            
            # تنظيف الطلبات المعالجة القديمة (أكثر من 60 يوم)
            self.cursor.execute('''
                DELETE FROM processed_orders 
                WHERE datetime(processed_at) < datetime('now', '-60 days')
            ''')
            
            self.conn.commit()
            
            # إحصائيات التنظيف
            self.cursor.execute('SELECT COUNT(*) FROM order_monitoring')
            monitoring_count = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT COUNT(*) FROM isolated_orders')
            isolated_count = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT COUNT(*) FROM processed_orders')
            processed_count = self.cursor.fetchone()[0]
            
            print(f"✅ تم تنظيف البيانات المكررة:")
            print(f"   📊 سجلات المراقبة: {monitoring_count}")
            print(f"   🚨 الطلبات المعزولة: {isolated_count}")
            print(f"   ✅ الطلبات المعالجة: {processed_count}")
            
            return True
            
        except Exception as e:
            print(f"❌ خطأ في تنظيف البيانات المكررة: {e}")
            return False

    def sync_unique_check_table(self):
        """مزامنة جدول التحقق من التفرد مع جدول الطلبات"""
        try:
            print("🔄 مزامنة جدول التحقق من التفرد...")
            
            # إدراج الطلبات الموجودة في جدول التحقق من التفرد
            self.cursor.execute('''
                INSERT OR IGNORE INTO orders_unique_check 
                (wasl_number, order_number, customer_id, last_updated)
                SELECT DISTINCT wasl_number, order_number, customer_id, 
                       DATETIME('now') as last_updated
                FROM orders
            ''')
            
            self.conn.commit()
            
            # إحصائيات المزامنة
            self.cursor.execute('SELECT COUNT(*) FROM orders_unique_check')
            unique_count = self.cursor.fetchone()[0]
            
            print(f"✅ تم مزامنة {unique_count} طلب في جدول التحقق من التفرد")
            return True
            
        except Exception as e:
            print(f"❌ خطأ في مزامنة جدول التحقق من التفرد: {e}")
            return False

    def get_duplicate_statistics(self):
        """الحصول على إحصائيات التكرار"""
        try:
            stats = {}
            
            # إحصائيات التكرار في الطلبات
            self.cursor.execute('''
                SELECT COUNT(*) as total_orders,
                       COUNT(DISTINCT wasl_number || '_' || order_number) as unique_orders
                FROM orders
            ''')
            
            order_stats = self.cursor.fetchone()
            stats['orders'] = {
                'total': order_stats[0],
                'unique': order_stats[1],
                'duplicates': order_stats[0] - order_stats[1]
            }
            
            # إحصائيات التكرار في المراقبة
            self.cursor.execute('''
                SELECT COUNT(*) as total_changes,
                       COUNT(DISTINCT wasl_number || '_' || order_number || '_' || change_type) as unique_changes
                FROM order_monitoring
            ''')
            
            monitoring_stats = self.cursor.fetchone()
            stats['monitoring'] = {
                'total': monitoring_stats[0],
                'unique': monitoring_stats[1],
                'duplicates': monitoring_stats[0] - monitoring_stats[1]
            }
            
            # إحصائيات التكرار في المعزولة
            self.cursor.execute('''
                SELECT COUNT(*) as total_isolated,
                       COUNT(DISTINCT wasl_number || '_' || order_number || '_' || reason) as unique_isolated
                FROM isolated_orders
            ''')
            
            isolated_stats = self.cursor.fetchone()
            stats['isolated'] = {
                'total': isolated_stats[0],
                'unique': isolated_stats[1],
                'duplicates': isolated_stats[0] - isolated_stats[1]
            }
            
            return stats
            
        except Exception as e:
            print(f"❌ خطأ في الحصول على إحصائيات التكرار: {e}")
            return {}

    def search_customer_orders(self, customer_id, customer_name, start_date, end_date):
        """البحث السريع عن طلبات عميل محدد"""
        try:
            # تحسين بيانات البحث للسرعة
            data = {
                'city': '',
                'date_add': start_date,
                'to_date_add': end_date,
                'date_add_mandob': '',
                'from_time': '',
                'to_time': '',
                'id_list': '',
                'id': '',
                'id_wasl': '',
                'name_customer': '',
                'phone_customer': '',
                'id_client': str(customer_id),
                'id_mandob': '',
                'wasl_search': ''
            }

            # إرسال طلب البحث مع تحسين الأداء
            response = self.session.post(
                f"{self.base_url}search_wasl.php",
                data=data,
                headers={
                    'Origin': 'https://alkarar-exp.com',
                    'Referer': 'https://alkarar-exp.com/postsearch_wasl.php',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0'
                },
                timeout=30  # تحديد timeout للسرعة
            )

            # تحليل النتائج
            orders = self.parse_orders_table(response.text)
            return orders

        except requests.exceptions.Timeout:
            print(f"⏰ انتهت مهلة الطلب للعميل {customer_name}")
            return []
        except Exception as error:
            print(f"❌ خطأ في البحث عن طلبات {customer_name}: {str(error)}")
            return []

    def parse_orders_table(self, html_content):
        """تحليل جدول الطلبات"""
        soup = BeautifulSoup(html_content, 'html.parser')
        orders = []

        # البحث عن جدول الطلبات
        table = soup.find('table', {'id': 'datatable1'})
        if not table:
            return orders

        rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) > 10:
                try:
                    order = {
                        'row_number': cells[0].get_text(strip=True),
                        'wasl_number': cells[4].get_text(strip=True),
                        'customer_name': cells[5].get_text(strip=True),
                        'mandob_name': cells[6].get_text(strip=True),
                        'city': cells[7].get_text(strip=True),
                        'area': cells[8].get_text(strip=True),
                        'customer_phone': cells[9].get_text(strip=True),
                        'total_amount': cells[10].get_text(strip=True),
                        'delivery_fee': cells[11].get_text(strip=True),
                        'net_amount': cells[12].get_text(strip=True),
                        'order_number': cells[14].get_text(strip=True),
                        'status': cells[16].get_text(strip=True),
                        'add_date': cells[24].get_text(strip=True),
                        'print_date': cells[25].get_text(strip=True),
                        'added_by': cells[26].get_text(strip=True)
                    }
                    orders.append(order)
                except IndexError:
                    continue

        return orders

    def check_if_order_exists(self, wasl_number, order_number, customer_id):
        """التحقق من وجود الطلب في قاعدة البيانات"""
        try:
            self.cursor.execute('''
                SELECT id FROM orders 
                WHERE wasl_number = ? AND order_number = ? AND customer_id = ?
            ''', (wasl_number, order_number, customer_id))
            return self.cursor.fetchone() is not None
        except Exception as e:
            print(f"❌ خطأ في التحقق من وجود الطلب: {e}")
            return False

    def check_if_change_recorded(self, wasl_number, order_number, change_type, old_amount, new_amount):
        """التحقق من تسجيل نفس التغيير مسبقاً"""
        try:
            # التحقق من وجود نفس التغيير خلال آخر 5 دقائق
            self.cursor.execute('''
                SELECT id FROM order_monitoring 
                WHERE wasl_number = ? AND order_number = ? AND change_type = ? 
                AND old_total_amount = ? AND new_total_amount = ?
                AND datetime(detected_at) >= datetime('now', '-5 minutes')
            ''', (wasl_number, order_number, change_type, old_amount, new_amount))
            return self.cursor.fetchone() is not None
        except Exception as e:
            print(f"❌ خطأ في التحقق من تسجيل التغيير: {e}")
            return False

    def check_if_order_isolated(self, wasl_number, order_number, reason):
        """التحقق من عزل الطلب مسبقاً لنفس السبب"""
        try:
            self.cursor.execute('''
                SELECT id FROM isolated_orders 
                WHERE wasl_number = ? AND order_number = ? AND reason = ?
            ''', (wasl_number, order_number, reason))
            return self.cursor.fetchone() is not None
        except Exception as e:
            print(f"❌ خطأ في التحقق من عزل الطلب: {e}")
            return False

    def clean_amount(self, amount_str):
        """دالة لتنظيف وتحويل المبالغ المالية"""
        if not amount_str or amount_str == '0':
            return 0.0
        cleaned = str(amount_str).replace(',', '').replace(' ', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def safe_insert_order(self, customer_id, order_data):
        """إدراج آمن للطلب مع منع التكرار"""
        try:
            wasl_number = order_data['wasl_number']
            order_number = order_data['order_number']
            
            # التحقق من وجود الطلب
            if self.check_if_order_exists(wasl_number, order_number, customer_id):
                print(f"⚠️  الطلب موجود مسبقاً: {wasl_number}")
                return False
            
            # تسجيل في جدول التحقق من التفرد
            self.cursor.execute('''
                INSERT OR IGNORE INTO orders_unique_check 
                (wasl_number, order_number, customer_id) 
                VALUES (?, ?, ?)
            ''', (wasl_number, order_number, customer_id))
            
            # إدراج الطلب الجديد
            self.cursor.execute('''
                INSERT INTO orders (
                    customer_id, wasl_number, order_number, customer_name,
                    mandob_name, city, area, customer_phone,
                    total_amount, delivery_fee, net_amount, status,
                    add_date, print_date, added_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                customer_id,
                order_data['wasl_number'],
                order_data['order_number'],
                order_data['customer_name'],
                order_data['mandob_name'],
                order_data['city'],
                order_data['area'],
                order_data['customer_phone'],
                self.clean_amount(order_data.get('total_amount', 0)),
                self.clean_amount(order_data.get('delivery_fee', 0)),
                self.clean_amount(order_data.get('net_amount', 0)),
                order_data['status'],
                order_data['add_date'],
                order_data['print_date'],
                order_data['added_by']
            ))
            
            print(f"✅ تم إدراج طلب جديد: {wasl_number}")
            return True
            
        except Exception as e:
            print(f"❌ خطأ في إدراج الطلب: {e}")
            return False

    def compare_orders(self, existing_orders, new_orders, customer_id, customer_name):
        """مقارنة سريعة وفعالة للطلبات مع منع التكرار"""
        changes = []
        isolated_orders = []
        
        # إنشاء فهرس للطلبات الجديدة للسرعة
        new_orders_index = {}
        for order in new_orders:
            key = f"{order['wasl_number']}_{order['order_number']}"
            new_orders_index[key] = order
        
        # فحص الطلبات الموجودة للتحديثات
        for key, existing in existing_orders.items():
            if key in new_orders_index:
                new_order = new_orders_index[key]
                
                new_total_amount = self.clean_amount(new_order['total_amount'])
                new_status = new_order['status']
                old_total_amount = existing['total_amount']
                old_status = existing['status']
                
                wasl_number = new_order['wasl_number']
                order_number = new_order['order_number']
                
                # فحص تغيير السعر مع منع التكرار
                if abs(new_total_amount - old_total_amount) > 0.01:
                    print(f"🚨 تغيير فوري في السعر - الوصل: {wasl_number}")
                    print(f"   💰 {old_total_amount} → {new_total_amount}")
                    
                    # التحقق من عدم تسجيل نفس التغيير مسبقاً
                    if not self.check_if_change_recorded(wasl_number, order_number, 'price_change', old_total_amount, new_total_amount):
                        # تسجيل التغيير فوراً
                        self.cursor.execute('''
                            INSERT OR IGNORE INTO order_monitoring 
                            (wasl_number, order_number, customer_id, customer_name, 
                             old_total_amount, new_total_amount, old_status, new_status, 
                             change_type, customer_phone, city, area)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            wasl_number, order_number, customer_id, customer_name,
                            old_total_amount, new_total_amount, old_status, new_status, 
                            'price_change', new_order.get('customer_phone', ''), 
                            new_order.get('city', ''), new_order.get('area', '')
                        ))
                        
                        # التحقق من عدم عزل الطلب مسبقاً لنفس السبب
                        isolation_reason = f'تغيير فوري في السعر من {old_total_amount} إلى {new_total_amount}'
                        if not self.check_if_order_isolated(wasl_number, order_number, isolation_reason):
                            # عزل الطلب فوراً
                            self.cursor.execute('''
                                INSERT OR IGNORE INTO isolated_orders 
                                (wasl_number, order_number, customer_id, customer_name, 
                                 total_amount, status, reason, customer_phone, city, area)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                wasl_number, order_number, customer_id, customer_name,
                                new_total_amount, new_status, isolation_reason,
                                new_order.get('customer_phone', ''), 
                                new_order.get('city', ''), new_order.get('area', '')
                            ))
                            
                            isolated_orders.append({
                                'wasl_number': wasl_number,
                                'old_price': old_total_amount,
                                'new_price': new_total_amount,
                                'customer_name': customer_name
                            })
                        
                        changes.append({
                            'type': 'price_change',
                            'wasl_number': wasl_number,
                            'old_price': old_total_amount,
                            'new_price': new_total_amount,
                            'customer_name': customer_name
                        })
                        
                        print(f"✅ تم تسجيل تغيير السعر: {wasl_number}")
                    else:
                        print(f"⚠️  تم تجاهل التغيير المكرر: {wasl_number}")
                    
                    # تحديث الطلب
                    self.cursor.execute('''
                        UPDATE orders 
                        SET total_amount = ?, status = ?
                        WHERE wasl_number = ? AND order_number = ?
                    ''', (new_total_amount, new_status, wasl_number, order_number))
                    
                    # تحديث البيانات المحلية
                    existing_orders[key]['total_amount'] = new_total_amount
                    existing_orders[key]['status'] = new_status
                
                # فحص تغيير الحالة مع منع التكرار
                elif new_status != old_status:
                    print(f"📝 تغيير فوري في الحالة - الوصل: {wasl_number}")
                    print(f"   🔄 {old_status} → {new_status}")
                    
                    # التحقق من عدم تسجيل نفس التغيير مسبقاً
                    if not self.check_if_change_recorded(wasl_number, order_number, 'status_change', old_total_amount, new_total_amount):
                        self.cursor.execute('''
                            INSERT OR IGNORE INTO order_monitoring 
                            (wasl_number, order_number, customer_id, customer_name, 
                             old_total_amount, new_total_amount, old_status, new_status, 
                             change_type, customer_phone, city, area)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            wasl_number, order_number, customer_id, customer_name,
                            old_total_amount, new_total_amount, old_status, new_status, 
                            'status_change', new_order.get('customer_phone', ''), 
                            new_order.get('city', ''), new_order.get('area', '')
                        ))
                        
                        changes.append({
                            'type': 'status_change',
                            'wasl_number': wasl_number,
                            'old_status': old_status,
                            'new_status': new_status,
                            'customer_name': customer_name
                        })
                        
                        print(f"✅ تم تسجيل تغيير الحالة: {wasl_number}")
                    else:
                        print(f"⚠️  تم تجاهل تغيير الحالة المكرر: {wasl_number}")
                    
                    # تحديث الطلب
                    self.cursor.execute('''
                        UPDATE orders 
                        SET status = ?
                        WHERE wasl_number = ? AND order_number = ?
                    ''', (new_status, wasl_number, order_number))
                    
                    # تحديث البيانات المحلية
                    existing_orders[key]['status'] = new_status
                
                # إزالة من الفهرس لتجنب المعالجة المتكررة
                del new_orders_index[key]
        
        # معالجة الطلبات الجديدة المتبقية مع منع التكرار
        for key, order in new_orders_index.items():
            wasl_number = order['wasl_number']
            print(f"🆕 طلب جديد فوري - الوصل: {wasl_number}")
            
            # إدراج آمن للطلب الجديد
            if self.safe_insert_order(customer_id, order):
                changes.append({
                    'type': 'new_order',
                    'wasl_number': wasl_number,
                    'customer_name': customer_name
                })
            else:
                print(f"⚠️  تم تجاهل الطلب المكرر: {wasl_number}")
        
        # حفظ التغييرات فوراً
        self.conn.commit()
        return changes, isolated_orders

    def monitor_orders(self, start_date, end_date, interval_seconds=1):
        """المراقبة المستمرة والفورية للطلبات - تنزيل مباشر مع منع التكرار"""
        print(f"🚀 بدء المراقبة المباشرة والمستمرة مع منع التكرار...")
        print(f"📅 الفترة: من {start_date} إلى {end_date}")
        print(f"⚡ فاصل المراقبة: {interval_seconds} ثانية (تنزيل فوري)")
        print(f"🔄 المراقبة ستعمل بشكل مستمر مع منع الحفظ المكرر")
        print("=" * 60)
        
        # مزامنة أولية للجدول
        self.sync_unique_check_table()
        
        cycle = 1
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        # تخزين آخر حالة لتجنب الطلبات المتكررة
        last_check_time = time.time()
        last_cleanup_time = time.time()
        
        while True:
            try:
                current_time = time.time()
                print(f"\n⚡ دورة المراقبة الفورية #{cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"🕐 الوقت منذ آخر فحص: {current_time - last_check_time:.2f} ثانية")
                print("-" * 50)
                
                # تنظيف البيانات المكررة كل 100 دورة
                if cycle % 100 == 0:
                    print("🧹 تنظيف البيانات المكررة...")
                    self.clean_duplicate_data()
                    last_cleanup_time = current_time
                
                # مزامنة جدول التحقق من التفرد كل 50 دورة
                if cycle % 50 == 0:
                    print("🔄 مزامنة جدول التحقق من التفرد...")
                    self.sync_unique_check_table()
                
                # الحصول على الطلبات الموجودة
                existing_orders = self.get_existing_orders()
                print(f"📊 عدد الطلبات في قاعدة البيانات: {len(existing_orders)}")
                
                total_changes = 0
                total_isolated = 0
                total_new_orders = 0
                
                # فحص كل عميل بشكل متوازي للسرعة
                for customer in self.customers:
                    customer_start_time = time.time()
                    print(f"🔍 فحص العميل: {customer['name']}")
                    
                    # الحصول على الطلبات الجديدة
                    new_orders = self.search_customer_orders(
                        customer['id'],
                        customer['name'],
                        start_date,
                        end_date
                    )
                    
                    customer_end_time = time.time()
                    print(f"   📦 عدد الطلبات: {len(new_orders)} (استغرق {customer_end_time - customer_start_time:.2f} ثانية)")
                    
                    # مقارنة الطلبات
                    changes, isolated = self.compare_orders(
                        existing_orders, 
                        new_orders, 
                        customer['id'], 
                        customer['name']
                    )
                    
                    # عد الطلبات الجديدة
                    new_orders_count = len([c for c in changes if c['type'] == 'new_order'])
                    
                    total_changes += len(changes)
                    total_isolated += len(isolated)
                    total_new_orders += new_orders_count
                    
                    if len(changes) > 0:
                        print(f"   ⚠️  تغييرات مكتشفة: {len(changes)}")
                        for change in changes:
                            if change['type'] == 'new_order':
                                print(f"      🆕 طلب جديد: {change['wasl_number']}")
                            elif change['type'] == 'price_change':
                                print(f"      💰 تغيير سعر: {change['wasl_number']} ({change['old_price']} → {change['new_price']})")
                            elif change['type'] == 'status_change':
                                print(f"      📝 تغيير حالة: {change['wasl_number']} ({change['old_status']} → {change['new_status']})")
                    
                    # تقليل الانتظار بين العملاء للسرعة
                    time.sleep(0.2)
                
                # إعادة تعيين عداد الأخطاء عند النجاح
                consecutive_errors = 0
                last_check_time = current_time
                
                # استخدام الدالة الجديدة لعرض إحصائيات الأداء
                self.print_performance_stats(cycle, current_time, total_changes, total_new_orders, total_isolated, ultra_fast=False)
                
                # إحصائيات أداء تفصيلية مع إحصائيات التكرار
                if cycle % 10 == 0:
                    print(f"\n📈 إحصائيات الأداء (آخر 10 دورات):")
                    print(f"   ⚡ معدل المراقبة: {10 / (10 * interval_seconds):.2f} دورة/ثانية")
                    print(f"   📊 إجمالي الدورات: {cycle}")
                    print(f"   ⏱️  متوسط زمن الدورة: {(time.time() - current_time):.2f} ثانية")
                    
                    # عرض إحصائيات التكرار كل 20 دورة
                    if cycle % 20 == 0:
                        duplicate_stats = self.get_duplicate_statistics()
                        if duplicate_stats:
                            print(f"\n📊 إحصائيات منع التكرار:")
                            print(f"   🔄 طلبات مكررة محذوفة: {duplicate_stats['orders']['duplicates']}")
                            print(f"   📈 تغييرات مكررة محذوفة: {duplicate_stats['monitoring']['duplicates']}")
                            print(f"   🚨 معزولة مكررة محذوفة: {duplicate_stats['isolated']['duplicates']}")
                
                print(f"\n⏳ انتظار {interval_seconds} ثانية للدورة التالية...")
                time.sleep(interval_seconds)
                cycle += 1
                
            except KeyboardInterrupt:
                print("\n⏹️  تم إيقاف المراقبة بواسطة المستخدم")
                break
            except Exception as e:
                consecutive_errors += 1
                print(f"❌ خطأ في المراقبة (خطأ #{consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"⚠️  عدد كبير من الأخطاء المتتالية ({consecutive_errors})")
                    print("🔄 إعادة تعيين الاتصال...")
                    try:
                        self.close_connection()
                        time.sleep(5)
                        if self.create_connection():
                            # إعادة مزامنة الجدول بعد إعادة الاتصال
                            self.sync_unique_check_table()
                            consecutive_errors = 0
                            print("✅ تم إعادة تعيين الاتصال بنجاح")
                    except:
                        print("❌ فشل في إعادة تعيين الاتصال")
                
                # انتظار أقل عند الأخطاء للحفاظ على السرعة
                error_wait_time = min(10, consecutive_errors * 2)
                print(f"⏳ إعادة المحاولة بعد {error_wait_time} ثانية...")
                time.sleep(error_wait_time)

    def monitor_orders_ultra_fast(self, start_date, end_date, interval_seconds=0.1):
        """المراقبة الفائقة السرعة - تنزيل كل عُشر ثانية مع منع التكرار"""
        print(f"🚀🚀 بدء المراقبة الفائقة السرعة مع منع التكرار...")
        print(f"📅 الفترة: من {start_date} إلى {end_date}")
        print(f"⚡⚡ فاصل المراقبة: {interval_seconds} ثانية (فائق السرعة)")
        print(f"🔄 مراقبة مستمرة بأقصى سرعة مع منع الحفظ المكرر")
        print("=" * 60)
        
        # مزامنة أولية للجدول
        self.sync_unique_check_table()
        
        cycle = 1
        consecutive_errors = 0
        max_consecutive_errors = 3
        last_cleanup_time = time.time()
        
        while True:
            try:
                start_time = time.time()
                print(f"\n⚡⚡ دورة فائقة السرعة #{cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                
                # تنظيف البيانات المكررة كل 500 دورة (للمراقبة فائقة السرعة)
                if cycle % 500 == 0:
                    print("🧹 تنظيف البيانات المكررة...")
                    self.clean_duplicate_data()
                    last_cleanup_time = start_time
                
                # مزامنة جدول التحقق من التفرد كل 200 دورة
                if cycle % 200 == 0:
                    print("🔄 مزامنة جدول التحقق من التفرد...")
                    self.sync_unique_check_table()
                
                # الحصول على الطلبات الموجودة
                existing_orders = self.get_existing_orders()
                
                total_changes = 0
                total_isolated = 0
                total_new_orders = 0
                
                # فحص العملاء بالتناوب للسرعة القصوى
                customers_to_check = self.customers[self.customer_rotation:self.customer_rotation+3]
                if len(customers_to_check) < 3:
                    customers_to_check.extend(self.customers[:3-len(customers_to_check)])
                
                for customer in customers_to_check:
                    customer_start = time.time()
                    
                    # فحص سريع للعميل
                    new_orders = self.search_customer_orders(
                        customer['id'],
                        customer['name'],
                        start_date,
                        end_date
                    )
                    
                    # مقارنة سريعة مع منع التكرار
                    changes, isolated = self.compare_orders(
                        existing_orders, 
                        new_orders, 
                        customer['id'], 
                        customer['name']
                    )
                    
                    new_orders_count = len([c for c in changes if c['type'] == 'new_order'])
                    total_changes += len(changes)
                    total_isolated += len(isolated)
                    total_new_orders += new_orders_count
                    
                    customer_time = time.time() - customer_start
                    
                    if len(changes) > 0:
                        print(f"⚡ {customer['name']}: {len(changes)} تغيير في {customer_time:.3f}s")
                        # عرض تفاصيل التغييرات للمراقبة فائقة السرعة
                        for change in changes:
                            if change['type'] == 'new_order':
                                print(f"   🆕 طلب جديد: {change['wasl_number']}")
                            elif change['type'] == 'price_change':
                                print(f"   💰 تغيير سعر: {change['wasl_number']}")
                            elif change['type'] == 'status_change':
                                print(f"   📝 تغيير حالة: {change['wasl_number']}")
                
                # تحديث دوران العملاء
                self.customer_rotation = (self.customer_rotation + 3) % len(self.customers)
                
                # إعادة تعيين عداد الأخطاء عند النجاح
                consecutive_errors = 0
                
                # استخدام الدالة الجديدة لعرض إحصائيات الأداء
                self.print_performance_stats(cycle, start_time, total_changes, total_new_orders, total_isolated, ultra_fast=True)
                
                # إحصائيات منع التكرار كل 1000 دورة
                if cycle % 1000 == 0:
                    duplicate_stats = self.get_duplicate_statistics()
                    if duplicate_stats:
                        print(f"\n📊 إحصائيات منع التكرار (فائق السرعة):")
                        print(f"   🔄 طلبات مكررة محذوفة: {duplicate_stats['orders']['duplicates']}")
                        print(f"   📈 تغييرات مكررة محذوفة: {duplicate_stats['monitoring']['duplicates']}")
                        print(f"   🚨 معزولة مكررة محذوفة: {duplicate_stats['isolated']['duplicates']}")
                
                time.sleep(interval_seconds)
                cycle += 1
                
            except KeyboardInterrupt:
                print("\n⏹️  تم إيقاف المراقبة الفائقة")
                break
            except Exception as e:
                consecutive_errors += 1
                print(f"❌ خطأ فائق السرعة #{consecutive_errors}: {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    print("🔄 إعادة تعيين الاتصال...")
                    try:
                        self.close_connection()
                        time.sleep(2)
                        if self.create_connection():
                            # إعادة مزامنة الجدول بعد إعادة الاتصال
                            self.sync_unique_check_table()
                            consecutive_errors = 0
                    except:
                        pass
                
                time.sleep(min(5, consecutive_errors))

    def get_isolated_orders(self):
        """الحصول على الطلبات المعزولة"""
        try:
            self.cursor.execute('''
                SELECT wasl_number, order_number, customer_name, total_amount, 
                       status, reason, isolated_at
                FROM isolated_orders
                ORDER BY isolated_at DESC
            ''')
            return self.cursor.fetchall()
        except Exception as e:
            print(f"❌ خطأ في الحصول على الطلبات المعزولة: {e}")
            return []

    def get_monitoring_log(self, limit=50):
        """الحصول على سجل المراقبة"""
        try:
            self.cursor.execute('''
                SELECT wasl_number, customer_name, old_total_amount, new_total_amount,
                       old_status, new_status, change_type, detected_at
                FROM order_monitoring
                ORDER BY detected_at DESC
                LIMIT ?
            ''', (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"❌ خطأ في الحصول على سجل المراقبة: {e}")
            return []

    def get_monitoring_stats(self):
        """الحصول على إحصائيات المراقبة في الوقت الفعلي"""
        try:
            stats = {}
            
            # إحصائيات المراقبة
            self.cursor.execute('''
                SELECT 
                    COUNT(*) as total_changes,
                    COUNT(CASE WHEN change_type = 'price_change' THEN 1 END) as price_changes,
                    COUNT(CASE WHEN change_type = 'status_change' THEN 1 END) as status_changes,
                    COUNT(CASE WHEN change_type = 'new_order' THEN 1 END) as new_orders,
                    COUNT(CASE WHEN DATE(detected_at) = DATE('now') THEN 1 END) as today_changes
                FROM order_monitoring
            ''')
            
            monitoring_stats = self.cursor.fetchone()
            stats['monitoring'] = {
                'total_changes': monitoring_stats[0] or 0,
                'price_changes': monitoring_stats[1] or 0,
                'status_changes': monitoring_stats[2] or 0,
                'new_orders': monitoring_stats[3] or 0,
                'today_changes': monitoring_stats[4] or 0
            }
            
            # إحصائيات الطلبات المعزولة
            self.cursor.execute('''
                SELECT 
                    COUNT(*) as total_isolated,
                    COUNT(CASE WHEN DATE(isolated_at) = DATE('now') THEN 1 END) as today_isolated
                FROM isolated_orders
            ''')
            
            isolated_stats = self.cursor.fetchone()
            stats['isolated'] = {
                'total_isolated': isolated_stats[0] or 0,
                'today_isolated': isolated_stats[1] or 0
            }
            
            # إحصائيات الطلبات المعالجة
            self.cursor.execute('''
                SELECT 
                    COUNT(*) as total_processed,
                    COUNT(CASE WHEN DATE(processed_at) = DATE('now') THEN 1 END) as today_processed
                FROM processed_orders
            ''')
            
            processed_stats = self.cursor.fetchone()
            stats['processed'] = {
                'total_processed': processed_stats[0] or 0,
                'today_processed': processed_stats[1] or 0
            }
            
            return stats
            
        except Exception as e:
            print(f"❌ خطأ في الحصول على إحصائيات المراقبة: {e}")
            return {}

    def print_performance_stats(self, cycle, start_time, total_changes, total_new_orders, total_isolated, ultra_fast=False):
        """طباعة إحصائيات الأداء"""
        current_time = time.time()
        cycle_time = current_time - start_time
        
        # حساب معدل الأداء
        if cycle > 0:
            avg_cycle_time = cycle_time
            cycles_per_minute = 60 / avg_cycle_time if avg_cycle_time > 0 else 0
            
            if total_changes > 0:
                print(f"🔥 دورة #{cycle}: {total_new_orders} جديد | {total_changes} تغيير | {total_isolated} معزول")
                print(f"   ⏱️  زمن الدورة: {cycle_time:.2f}s | معدل: {cycles_per_minute:.1f} دورة/دقيقة")
            elif not ultra_fast and cycle % 20 == 0:  # طباعة كل 20 دورة للمراقبة العادية
                print(f"✅ دورة #{cycle}: مراقبة مستمرة - {cycle_time:.2f}s")
            elif ultra_fast and cycle % 100 == 0:  # طباعة كل 100 دورة للمراقبة فائقة السرعة
                print(f"✅ دورة #{cycle}: مراقبة فائقة السرعة - {cycle_time:.3f}s")
        
        # إحصائيات تفصيلية
        stats_interval = 500 if ultra_fast else 100
        if cycle % stats_interval == 0:
            stats = self.get_monitoring_stats()
            if stats:
                print(f"\n📊 إحصائيات شاملة (دورة #{cycle}):")
                print(f"   📈 إجمالي التغييرات: {stats['monitoring']['total_changes']}")
                print(f"   💰 تغييرات الأسعار: {stats['monitoring']['price_changes']}")
                print(f"   📝 تغييرات الحالة: {stats['monitoring']['status_changes']}")
                print(f"   🆕 طلبات جديدة: {stats['monitoring']['new_orders']}")
                print(f"   🚨 طلبات معزولة: {stats['isolated']['total_isolated']}")
                print(f"   ✅ طلبات معالجة: {stats['processed']['total_processed']}")
                print(f"   📅 تغييرات اليوم: {stats['monitoring']['today_changes']}")

    def close_connection(self):
        """إغلاق الاتصال"""
        if self.conn:
            self.conn.close()
            print("✅ تم إغلاق الاتصال بقاعدة البيانات")

def main():
    """تشغيل المراقبة الفورية والمستمرة مع منع التكرار"""
    session_id = '9d427774521140c6f62c431743d91572'
    
    # حساب التواريخ تلقائياً - من غد إلى قبل شهر بالضبط
    from datetime import datetime, timedelta
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    one_month_ago = today - timedelta(days=30)
    
    # تنسيق التواريخ بالشكل الأمريكي MM/DD/YYYY
    end_date = tomorrow.strftime('%m/%d/%Y')
    start_date = one_month_ago.strftime('%m/%d/%Y')
    
    print(f"🚀 بدء المراقبة الفورية والمستمرة مع منع التكرار")
    print(f"📅 الفترة التلقائية: من {start_date} إلى {end_date}")
    print(f"⚡ تنزيل فوري - مراقبة كل ثانية واحدة")
    print(f"🔄 إعادة التشغيل التلقائي عند الأخطاء")
    print(f"🚫 منع الحفظ المكرر للبيانات")
    
    interval_seconds = 1  # مراقبة فورية كل ثانية
    
    # إعداد أولي لقاعدة البيانات
    print("🔧 إعداد قاعدة البيانات...")
    try:
        monitor = OrderMonitor(session_id)
        if monitor.create_connection():
            # مزامنة جدول التحقق من التفرد
            monitor.sync_unique_check_table()
            
            # تنظيف البيانات المكررة
            monitor.clean_duplicate_data()
            
            # عرض إحصائيات التكرار الأولية
            duplicate_stats = monitor.get_duplicate_statistics()
            if duplicate_stats:
                print(f"📊 إحصائيات قاعدة البيانات:")
                print(f"   🔄 إجمالي الطلبات: {duplicate_stats['orders']['total']} ({duplicate_stats['orders']['unique']} فريد)")
                print(f"   📈 إجمالي التغييرات: {duplicate_stats['monitoring']['total']} ({duplicate_stats['monitoring']['unique']} فريد)")
                print(f"   🚨 إجمالي المعزولة: {duplicate_stats['isolated']['total']} ({duplicate_stats['isolated']['unique']} فريد)")
            
            monitor.close_connection()
            print("✅ تم إعداد قاعدة البيانات بنجاح")
        else:
            print("❌ فشل في إعداد قاعدة البيانات")
    except Exception as e:
        print(f"❌ خطأ في إعداد قاعدة البيانات: {e}")
    
    # حلقة لإعادة التشغيل التلقائي
    while True:
        try:
            monitor = OrderMonitor(session_id)
            
            if monitor.create_connection():
                print("✅ تم الاتصال بقاعدة البيانات بنجاح")
                try:
                    monitor.monitor_orders(start_date, end_date, interval_seconds)
                except KeyboardInterrupt:
                    print("\n⏹️  تم إيقاف البرنامج بواسطة المستخدم")
                    break
                finally:
                    monitor.close_connection()
            else:
                print("❌ فشل في الاتصال بقاعدة البيانات")
                print("🔄 إعادة المحاولة بعد 10 ثوانٍ...")
                time.sleep(10)
                
        except Exception as e:
            print(f"❌ خطأ عام في البرنامج: {e}")
            print("🔄 إعادة تشغيل البرنامج تلقائياً بعد 10 ثوانٍ...")
            time.sleep(10)
    
    print("🏁 تم إنهاء البرنامج")

if __name__ == "__main__":
    main() 