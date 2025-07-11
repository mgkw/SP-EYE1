#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import sqlite3
import json
import threading
import time
from datetime import datetime
import subprocess
import os
from test import CustomerOrdersSearch
from monitor_orders import OrderMonitor

# إضافة متغير لتتبع حالة المراقبة
monitoring_active = False
monitoring_threads = []

def format_iraqi_dinar(amount):
    """تنسيق المبلغ بالدينار العراقي مع فواصل الآلاف"""
    if amount is None or amount == 0:
        return "0 دينار"
    
    # تحويل إلى رقم
    try:
        num = float(amount)
    except:
        return "0 دينار"
    
    # تنسيق الرقم بفواصل كل 3 أرقام
    formatted_num = "{:,}".format(int(num))
    
    # إضافة "دينار" في النهاية
    return f"{formatted_num} دينار"

def get_status_color(status):
    """تحديد لون الحالة بناءً على نوعها"""
    status_colors = {
        'قيد التنفيذ': 'warning',
        'تم التسليم': 'success',
        'واصل جزئي': 'info',
        'مؤجل': 'secondary',
        'رفض': 'danger',
        'راجع مخزن': 'primary',
        'راجع جزئي': 'info',
        'راجع عميل': 'warning',
        'تم محاسبة العميل': 'success',
        'تم محاسبة المندوب': 'success',
        'تم المحاسبة': 'success'
    }
    return status_colors.get(status, 'secondary')

def get_custom_status_class(status):
    """تحديد كلاس CSS المخصص للحالة بناءً على نظام الألوان الجديد"""
    status_classes = {
        'تم المحاسبة': 'status-accounted',
        'تم محاسبة المندوب': 'status-mandob-accounted', 
        'تم محاسبة العميل': 'status-customer-accounted',
        'تم التسليم': 'status-delivered',
        'رفض': 'status-rejected',
        'راجع جزئي': 'status-partial-return-yellow',
        'راجع مخزن': 'status-warehouse-return',
        'مؤجل': 'status-delayed',
        'قيد التنفيذ': 'status-in-progress',
        'غير مؤكد': 'status-unconfirmed',
        'واصل جزئي': 'status-partial-delivered'
    }
    return status_classes.get(status, 'status-unconfirmed')

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# إضافة الدوال إلى Jinja2
app.jinja_env.globals.update(
    format_iraqi_dinar=format_iraqi_dinar,
    get_status_color=get_status_color,
    get_custom_status_class=get_custom_status_class
)

# إعدادات قاعدة البيانات
DB_NAME = 'customer_orders.db'

class DatabaseManager:
    def __init__(self):
        self.db_name = DB_NAME
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def get_customers_stats(self):
        """الحصول على إحصائيات العملاء (غير المكتملة)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, c.name, COUNT(o.id) as orders_count, 
                   SUM(o.total_amount) as total_amount,
                   SUM(o.delivery_fee) as delivery_fee,
                   SUM(o.net_amount) as net_amount
            FROM customers c
            LEFT JOIN orders o ON c.id = o.customer_id AND o.status NOT IN ('تم المحاسبة', 'راجع عميل')
            GROUP BY c.id, c.name
            ORDER BY orders_count DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        stats = []
        for row in results:
            stats.append({
                'id': row[0],  # معرف العميل
                'name': row[1],  # اسم العميل
                'orders_count': row[2] or 0,
                'total_amount': row[3] or 0,
                'delivery_fee': row[4] or 0,
                'net_amount': row[5] or 0
            })
        
        return stats
    
    def get_customers_completed_stats(self):
        """الحصول على إحصائيات الطلبات المكتملة للعملاء"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, c.name, COUNT(o.id) as orders_count, 
                   SUM(o.total_amount) as total_amount,
                   SUM(o.delivery_fee) as delivery_fee,
                   SUM(o.net_amount) as net_amount
            FROM customers c
            LEFT JOIN orders o ON c.id = o.customer_id AND o.status IN ('تم التسليم', 'تم محاسبة المندوب', 'الواصل جزئي')
            GROUP BY c.id, c.name
            ORDER BY orders_count DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        stats = []
        for row in results:
            stats.append({
                'id': row[0],  # معرف العميل
                'name': row[1],  # اسم العميل
                'orders_count': row[2] or 0,
                'total_amount': row[3] or 0,
                'delivery_fee': row[4] or 0,
                'net_amount': row[5] or 0
            })
        
        return stats
    
    def get_agent_commission_stats(self):
        """الحصول على إحصائيات مستحق العملاء من الطلبات المكتملة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                customer_name,
                COUNT(*) as orders_count,
                SUM(total_amount) as total_amount,
                SUM(delivery_fee) as delivery_fee,
                SUM(total_amount - delivery_fee) as net_amount,
                COUNT(CASE WHEN status = 'تم التسليم' THEN 1 END) as delivered_count,
                COUNT(CASE WHEN status = 'تم محاسبة المندوب' THEN 1 END) as mandob_accounted_count,
                SUM(CASE WHEN status = 'تم التسليم' THEN total_amount ELSE 0 END) as delivered_amount,
                SUM(CASE WHEN status = 'تم محاسبة المندوب' THEN total_amount ELSE 0 END) as mandob_accounted_amount
            FROM orders 
            WHERE status IN ('تم التسليم', 'تم محاسبة المندوب')
            GROUP BY customer_name
            ORDER BY total_amount DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        stats = []
        for row in results:
            total_amount = row[2] or 0
            delivery_fee = row[3] or 0
            # حساب المبلغ الصافي بشكل صحيح
            net_amount = total_amount - delivery_fee
            
            stats.append({
                'customer_name': row[0] or 'غير محدد',
                'orders_count': row[1] or 0,
                'total_amount': total_amount,
                'delivery_fee': delivery_fee,
                'net_amount': net_amount,
                'delivered_count': row[5] or 0,
                'mandob_accounted_count': row[6] or 0,
                'delivered_amount': row[7] or 0,
                'mandob_accounted_amount': row[8] or 0
            })
        
        return stats
    
    def get_recent_orders(self, limit=10):
        """الحصول على أحدث الطلبات"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT wasl_number, order_number, customer_name, 
                   total_amount, status, add_date, city,
                   mandob_name, area, customer_phone,
                   delivery_fee, net_amount, added_by
            FROM orders 
            ORDER BY add_date DESC 
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        orders = []
        for row in results:
            orders.append({
                'wasl_number': row[0],
                'order_number': row[1],
                'customer_name': row[2],
                'total_amount': row[3],
                'status': row[4],
                'add_date': row[5],
                'city': row[6],
                'mandob_name': row[7],
                'area': row[8],
                'customer_phone': row[9],
                'delivery_fee': row[10],
                'net_amount': row[11],
                'added_by': row[12]
            })
        
        return orders

    def get_today_orders(self):
        """الحصول على طلبات اليوم فقط"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # الحصول على التاريخ الحالي بالتنسيق المطلوب
        from datetime import datetime
        today = datetime.now().strftime('%Y/%m/%d')
        
        cursor.execute('''
            SELECT wasl_number, order_number, customer_name, 
                   total_amount, status, add_date, city,
                   mandob_name, area, customer_phone,
                   delivery_fee, net_amount, added_by
            FROM orders 
            WHERE add_date LIKE ?
            ORDER BY add_date DESC
        ''', (f'{today}%',))
        
        results = cursor.fetchall()
        conn.close()
        
        orders = []
        for row in results:
            orders.append({
                'wasl_number': row[0],
                'order_number': row[1],
                'customer_name': row[2],
                'total_amount': row[3],
                'status': row[4],
                'add_date': row[5],
                'city': row[6],
                'mandob_name': row[7],
                'area': row[8],
                'customer_phone': row[9],
                'delivery_fee': row[10],
                'net_amount': row[11],
                'added_by': row[12]
            })
        
        return orders

    def get_today_stats(self):
        """الحصول على إحصائيات اليوم"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # الحصول على التاريخ الحالي بالتنسيق المطلوب
        from datetime import datetime
        today = datetime.now().strftime('%Y/%m/%d')
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_amount,
                SUM(net_amount) as total_net_amount,
                COUNT(DISTINCT customer_name) as unique_customers
            FROM orders 
            WHERE add_date LIKE ?
        ''', (f'{today}%',))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'total_orders': result[0] or 0,
                'total_amount': result[1] or 0,
                'total_net_amount': result[2] or 0,
                'unique_customers': result[3] or 0
            }
        return {
            'total_orders': 0,
            'total_amount': 0,
            'total_net_amount': 0,
            'unique_customers': 0
        }
    
    def get_yesterday_stats(self):
        """الحصول على إحصائيات أمس"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # الحصول على تاريخ أمس
        from datetime import datetime, timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y/%m/%d')
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_amount,
                SUM(net_amount) as total_net_amount,
                COUNT(DISTINCT customer_name) as unique_customers
            FROM orders 
            WHERE add_date LIKE ?
        ''', (f'{yesterday}%',))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'total_orders': result[0] or 0,
                'total_amount': result[1] or 0,
                'total_net_amount': result[2] or 0,
                'unique_customers': result[3] or 0
            }
        return {
            'total_orders': 0,
            'total_amount': 0,
            'total_net_amount': 0,
            'unique_customers': 0
        }

    def get_week_stats(self):
        """الحصول على إحصائيات الأسبوع الحالي"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # الحصول على تاريخ بداية الأسبوع (السبت)
        from datetime import datetime, timedelta
        today = datetime.now()
        days_since_saturday = (today.weekday() + 2) % 7
        week_start = today - timedelta(days=days_since_saturday)
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_amount,
                SUM(net_amount) as total_net_amount,
                COUNT(DISTINCT customer_name) as unique_customers
            FROM orders 
            WHERE add_date >= ?
        ''', (week_start.strftime('%Y/%m/%d'),))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'total_orders': result[0] or 0,
                'total_amount': result[1] or 0,
                'total_net_amount': result[2] or 0,
                'unique_customers': result[3] or 0
            }
        return {
            'total_orders': 0,
            'total_amount': 0,
            'total_net_amount': 0,
            'unique_customers': 0
        }

    def get_month_stats(self):
        """الحصول على إحصائيات الشهر الحالي"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # الحصول على تاريخ بداية الشهر
        from datetime import datetime
        today = datetime.now()
        month_start = today.replace(day=1)
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_amount,
                SUM(net_amount) as total_net_amount,
                COUNT(DISTINCT customer_name) as unique_customers
            FROM orders 
            WHERE add_date >= ?
        ''', (month_start.strftime('%Y/%m/%d'),))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'total_orders': result[0] or 0,
                'total_amount': result[1] or 0,
                'total_net_amount': result[2] or 0,
                'unique_customers': result[3] or 0
            }
        return {
            'total_orders': 0,
            'total_amount': 0,
            'total_net_amount': 0,
            'unique_customers': 0
        }
    
    def get_isolated_orders(self):
        """الحصول على الطلبات المعزولة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT wasl_number, order_number, customer_name, 
                   total_amount, status, reason, isolated_at,
                   customer_phone, city, area
            FROM isolated_orders
            ORDER BY isolated_at DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        orders = []
        for row in results:
            orders.append({
                'wasl_number': row[0],
                'order_number': row[1],
                'customer_name': row[2],
                'total_amount': row[3],
                'status': row[4],
                'reason': row[5],
                'isolated_at': row[6],
                'customer_phone': row[7],
                'city': row[8],
                'area': row[9]
            })
        
        return orders
    
    def get_monitoring_log(self, limit=100):
        """الحصول على سجل المراقبة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT wasl_number, customer_name, old_total_amount, new_total_amount,
                   old_status, new_status, change_type, detected_at,
                   customer_phone, city, area
            FROM order_monitoring
            ORDER BY detected_at DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in results:
            logs.append({
                'wasl_number': row[0],
                'customer_name': row[1],
                'old_total_amount': row[2],
                'new_total_amount': row[3],
                'old_status': row[4],
                'new_status': row[5],
                'change_type': row[6],
                'detected_at': row[7],
                'customer_phone': row[8],
                'city': row[9],
                'area': row[10]
            })
        
        return logs
    
    def get_customer_orders(self, customer_id):
        """الحصول على طلبات العميل (غير المكتملة)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT o.wasl_number, o.order_number, o.customer_name, 
                   o.total_amount, o.status, o.add_date, o.city,
                   o.mandob_name, o.area, o.customer_phone,
                   o.delivery_fee, o.net_amount, o.added_by
            FROM orders o
            WHERE o.customer_id = ? AND o.status NOT IN ('تم المحاسبة', 'راجع عميل')
            ORDER BY o.id DESC
        ''', (customer_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        orders = []
        for row in results:
            orders.append({
                'wasl_number': row[0],
                'order_number': row[1],
                'customer_name': row[2],
                'total_amount': row[3],
                'status': row[4],
                'add_date': row[5],
                'city': row[6],
                'mandob_name': row[7],
                'area': row[8],
                'customer_phone': row[9],
                'delivery_fee': row[10],
                'net_amount': row[11],
                'added_by': row[12]
            })
        
        return orders
    
    def get_customer_by_id(self, customer_id):
        """الحصول على معلومات العميل"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name FROM customers WHERE id = ?', (customer_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {'id': result[0], 'name': result[1]}
        return None
    
    def get_customer_archived_orders(self, customer_id):
        """الحصول على طلبات أرشيف العميل (المكتملة والمراجعة)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT o.wasl_number, o.order_number, o.customer_name, 
                   o.total_amount, o.status, o.add_date, o.city,
                   o.mandob_name, o.area, o.customer_phone,
                   o.delivery_fee, o.net_amount, o.added_by
            FROM orders o
            WHERE o.customer_id = ? AND (o.status = 'تم المحاسبة' OR o.status = 'راجع عميل')
            ORDER BY o.id DESC
        ''', (customer_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        orders = []
        for row in results:
            orders.append({
                'wasl_number': row[0],
                'order_number': row[1],
                'customer_name': row[2],
                'total_amount': row[3],
                'status': row[4],
                'add_date': row[5],
                'city': row[6],
                'mandob_name': row[7],
                'area': row[8],
                'customer_phone': row[9],
                'delivery_fee': row[10],
                'net_amount': row[11],
                'added_by': row[12]
            })
        
        return orders
    
    def get_database_stats(self):
        """الحصول على إحصائيات قاعدة البيانات"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # عدد الطلبات
        cursor.execute('SELECT COUNT(*) FROM orders')
        total_orders = cursor.fetchone()[0]
        
        # إجمالي المبالغ
        cursor.execute('SELECT SUM(total_amount), SUM(delivery_fee), SUM(net_amount) FROM orders')
        amounts = cursor.fetchone()
        total_amount = amounts[0] or 0
        total_delivery = amounts[1] or 0
        total_net = amounts[2] or 0
        
        # عدد الطلبات المعزولة
        cursor.execute('SELECT COUNT(*) FROM isolated_orders')
        isolated_count = cursor.fetchone()[0]
        
        # عدد التغييرات
        cursor.execute('SELECT COUNT(*) FROM order_monitoring')
        changes_count = cursor.fetchone()[0]
        
        # عدد العملاء
        cursor.execute('SELECT COUNT(*) FROM customers')
        total_customers = cursor.fetchone()[0]
        
        # عدد الطلبات المحذوفة
        try:
            cursor.execute('SELECT COUNT(*) FROM deleted_orders')
            deleted_count = cursor.fetchone()[0] or 0
        except:
            deleted_count = 0
        
        conn.close()
        
        return {
            'total_orders': total_orders,
            'total_amount': total_amount,
            'total_delivery': total_delivery,
            'total_net': total_net,
            'isolated_count': isolated_count,
            'changes_count': changes_count,
            'total_customers': total_customers,
            'deleted_count': deleted_count
        }
    
    def get_status_statistics(self):
        """الحصول على إحصائيات الحالات"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, COUNT(*) as count, SUM(total_amount) as total_amount
            FROM orders
            GROUP BY status
            ORDER BY count DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        stats = []
        for row in results:
            stats.append({
                'status': row[0],
                'count': row[1],
                'total_amount': row[2] or 0
            })
        
        return stats

    def get_suspended_orders(self):
        """الحصول على الطلبات المعلقة التي تحتاج متابعة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # الحصول على التاريخ الحالي
        from datetime import datetime, timedelta
        current_date = datetime.now()
        
        # استعلام للطلبات المعلقة مع إضافة المندوب وترتيب من الأحدث إلى الأقدم
        cursor.execute('''
            SELECT o.wasl_number, o.order_number, o.customer_name, 
                   o.total_amount, o.status, o.add_date, o.city,
                   o.customer_phone, o.area, o.mandob_name
            FROM orders o
            WHERE o.status IN ('قيد التنفيذ', 'مؤجل', 'رفض', 'راجع مخزن', 'تم محاسبة المندوب', 'تم التسليم')
            ORDER BY o.add_date DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        orders = []
        for row in results:
            # تحليل التاريخ - تنسيق YYYY/MM/DD
            try:
                order_date = datetime.strptime(row[5], '%Y/%m/%d')
                days_diff = (current_date - order_date).days
                
                suspension_reason = ""
                if row[4] == 'قيد التنفيذ' and days_diff > 1:
                    suspension_reason = f"قيد التنفيذ منذ {days_diff} يوم"
                elif row[4] == 'مؤجل' and days_diff > 2:
                    suspension_reason = f"مؤجل منذ {days_diff} يوم"
                elif row[4] == 'رفض' and days_diff > 7:
                    suspension_reason = f"رفض منذ {days_diff} يوم"
                elif row[4] == 'راجع مخزن' and days_diff > 2:
                    suspension_reason = f"راجع مخزن منذ {days_diff} يوم"
                elif row[4] == 'تم محاسبة المندوب' and days_diff > 2:
                    suspension_reason = f"تم محاسبة مندوب منذ {days_diff} يوم"
                elif row[4] == 'تم التسليم' and days_diff > 2:
                    suspension_reason = f"تم التسليم منذ {days_diff} يوم"
                
                # إضافة الطلب فقط إذا كان معلق
                if suspension_reason:
                    orders.append({
                        'wasl_number': row[0],
                        'order_number': row[1],
                        'customer_name': row[2],
                        'total_amount': row[3],
                        'status': row[4],
                        'add_date': row[5],
                        'city': row[6],
                        'customer_phone': row[7],
                        'area': row[8],
                        'mandob_name': row[9],
                        'suspension_reason': suspension_reason
                    })
                    
            except Exception as e:
                continue
        
        return orders

    def mark_isolated_order_processed(self, wasl_number):
        """تمييز الطلب المعزول كمعالج"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # التحقق من وجود الطلب في جدول الطلبات المعزولة
            cursor.execute('''
                SELECT id FROM isolated_orders 
                WHERE wasl_number = ?
            ''', (wasl_number,))
            
            if cursor.fetchone():
                # إضافة الطلب إلى جدول الطلبات المعالجة
                from datetime import datetime
                processed_at = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
                
                cursor.execute('''
                    INSERT OR REPLACE INTO processed_orders 
                    (wasl_number, processed_at, processed_by) 
                    VALUES (?, ?, ?)
                ''', (wasl_number, processed_at, 'user'))
                
                # حذف الطلب من جدول الطلبات المعزولة
                cursor.execute('''
                    DELETE FROM isolated_orders 
                    WHERE wasl_number = ?
                ''', (wasl_number,))
                
                conn.commit()
                conn.close()
                return True
            else:
                conn.close()
                return False
                
        except Exception as e:
            conn.close()
            print(f"خطأ في تمييز الطلب كمعالج: {e}")
            return False

    def get_processed_orders(self):
        """الحصول على الطلبات المعالجة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT po.wasl_number, po.processed_at, po.processed_by,
                       o.order_number, o.customer_name, o.total_amount, 
                       o.status, o.add_date, o.city, o.customer_phone, o.area
                FROM processed_orders po
                LEFT JOIN orders o ON po.wasl_number = o.wasl_number
                ORDER BY po.processed_at DESC
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            orders = []
            for row in results:
                orders.append({
                    'wasl_number': row[0],
                    'processed_at': row[1],
                    'processed_by': row[2],
                    'order_number': row[3],
                    'customer_name': row[4],
                    'total_amount': row[5],
                    'status': row[6],
                    'add_date': row[7],
                    'city': row[8],
                    'customer_phone': row[9],
                    'area': row[10]
                })
            
            return orders
            
        except Exception as e:
            conn.close()
            print(f"خطأ في الحصول على الطلبات المعالجة: {e}")
            return []

# إنشاء مجلد للقوالب
os.makedirs('templates', exist_ok=True)

# إنشاء قالب HTML الرئيسي
@app.route('/')
def index():
    db = DatabaseManager()
    
    # الحصول على جميع الإحصائيات
    stats = db.get_database_stats()
    customers_stats = db.get_customers_stats()
    recent_orders = db.get_recent_orders(10)
    today_stats = db.get_today_stats()
    yesterday_stats = db.get_yesterday_stats()
    week_stats = db.get_week_stats()
    month_stats = db.get_month_stats()
    
    # إحصائيات الحالات
    status_stats = db.get_status_statistics()
    
    # إحصائيات المراقبة
    monitoring_logs = db.get_monitoring_log(5)
    
    # إحصائيات الطلبات المعزولة
    isolated_orders = db.get_isolated_orders()
    
    return render_template('index.html', 
                         stats=stats, 
                         customers_stats=customers_stats,
                         recent_orders=recent_orders,
                         today_stats=today_stats,
                         yesterday_stats=yesterday_stats,
                         week_stats=week_stats,
                         month_stats=month_stats,
                         status_stats=status_stats,
                         monitoring_logs=monitoring_logs,
                         isolated_orders=isolated_orders)



@app.route('/today_orders')
def today_orders():
    db = DatabaseManager()
    today_orders = db.get_today_orders()
    today_stats = db.get_today_stats()
    yesterday_stats = db.get_yesterday_stats()
    week_stats = db.get_week_stats()
    month_stats = db.get_month_stats()
    
    return render_template('today_orders.html', 
                         orders=today_orders, 
                         stats=today_stats,
                         yesterday_stats=yesterday_stats,
                         week_stats=week_stats,
                         month_stats=month_stats)

@app.route('/isolated')
def isolated():
    db = DatabaseManager()
    orders = db.get_isolated_orders()
    return render_template('isolated.html', orders=orders)

@app.route('/monitoring')
def monitoring():
    db = DatabaseManager()
    logs = db.get_monitoring_log(100)
    return render_template('monitoring.html', logs=logs)

@app.route('/suspended')
def suspended():
    db = DatabaseManager()
    orders = db.get_suspended_orders()
    return render_template('suspended.html', orders=orders)

@app.route('/customers')
def customers():
    db = DatabaseManager()
    stats = db.get_customers_stats()
    completed_stats = db.get_customers_completed_stats()
    return render_template('customers.html', customers=stats, completed_stats=completed_stats)

@app.route('/agent_commission')
def agent_commission():
    db = DatabaseManager()
    customer_commission_stats = db.get_agent_commission_stats()
    
    # تصحيح الأخطاء - طباعة بيانات العاب ريمي
    for agent in customer_commission_stats:
        if agent['customer_name'] == 'العاب ريمي':
            print(f"DEBUG - العاب ريمي:")
            print(f"  عدد الطلبات: {agent['orders_count']}")
            print(f"  إجمالي المبالغ: {agent['total_amount']:,}")
            print(f"  رسوم التوصيل: {agent['delivery_fee']:,}")
            print(f"  المبلغ الصافي: {agent['net_amount']:,}")
            print(f"  المبلغ الصافي المحسوب: {agent['total_amount'] - agent['delivery_fee']:,}")
            break
    
    return render_template('agent_commission.html', agents=customer_commission_stats)

@app.route('/customer/<int:customer_id>')
def customer_orders(customer_id):
    """صفحة طلبات العميل"""
    db = DatabaseManager()
    customer = db.get_customer_by_id(customer_id)
    orders = db.get_customer_orders(customer_id)
    
    if not customer:
        flash('العميل غير موجود', 'danger')
        return redirect(url_for('customers'))
    
    return render_template('customer_orders.html', 
                         customer_name=customer['name'],
                         customer_id=customer_id,
                         orders=orders)

@app.route('/customer/<int:customer_id>/archive')
def customer_archive(customer_id):
    """صفحة أرشيف العميل - الطلبات المكتملة والمراجعة"""
    db = DatabaseManager()
    customer = db.get_customer_by_id(customer_id)
    archived_orders = db.get_customer_archived_orders(customer_id)
    
    if not customer:
        flash('العميل غير موجود', 'danger')
        return redirect(url_for('customers'))
    
    return render_template('customer_archive.html', 
                         customer_name=customer['name'],
                         customer_id=customer_id,
                         orders=archived_orders)

@app.route('/api/stats')
def api_stats():
    db = DatabaseManager()
    stats = db.get_database_stats()
    return jsonify(stats)

@app.route('/api/customers')
def api_customers():
    db = DatabaseManager()
    stats = db.get_customers_stats()
    return jsonify(stats)

@app.route('/api/orders')
def api_orders():
    db = DatabaseManager()
    orders = db.get_recent_orders(50)
    return jsonify(orders)

@app.route('/start_monitoring', methods=['POST'])
def start_monitoring():
    """تشغيل المراقبة المحسنة في الخلفية"""
    try:
        # تشغيل السكريبت في خيط منفصل مع تحسينات
        def run_monitoring():
            session_id = '9d427774521140c6f62c431743d91572'
            
            # حساب التواريخ تلقائياً - من غد إلى قبل شهر بالضبط
            from datetime import datetime, timedelta
            today = datetime.now()
            tomorrow = today + timedelta(days=1)
            one_month_ago = today - timedelta(days=30)
            
            # تنسيق التواريخ بالشكل الأمريكي MM/DD/YYYY
            end_date = tomorrow.strftime('%m/%d/%Y')
            start_date = one_month_ago.strftime('%m/%d/%Y')
            
            print(f"📅 الفترة التلقائية: من {start_date} إلى {end_date}")
            print(f"⚡ مراقبة محسنة - تنزيل كل ثانية واحدة")
            
            # حلقة لإعادة التشغيل التلقائي
            while True:
                try:
                    monitor = OrderMonitor(session_id)
                    if monitor.create_connection():
                        monitor.monitor_orders(start_date, end_date, interval_seconds=1)
                    else:
                        print("❌ فشل في الاتصال، إعادة المحاولة...")
                        time.sleep(10)
                except Exception as e:
                    print(f"❌ خطأ في المراقبة: {e}")
                    print("🔄 إعادة تشغيل تلقائي...")
                    time.sleep(10)
        
        thread = threading.Thread(target=run_monitoring)
        thread.daemon = True
        thread.start()
        
        flash('تم بدء المراقبة المحسنة بنجاح! (تنزيل كل ثانية)', 'success')
    except Exception as e:
        flash(f'خطأ في بدء المراقبة: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/run_script', methods=['POST'])
def run_script():
    """تشغيل سكريبت test.py"""
    try:
        # تشغيل السكريبت في خيط منفصل
        def run_test_script():
            subprocess.run(['python', 'test.py'], capture_output=True, text=True)
        
        thread = threading.Thread(target=run_test_script)
        thread.daemon = True
        thread.start()
        
        flash('تم تشغيل السكريبت بنجاح!', 'success')
    except Exception as e:
        flash(f'خطأ في تشغيل السكريبت: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/delete_order/<wasl_number>')
def delete_order(wasl_number):
    """حذف الطلب من النظام الخارجي وقاعدة البيانات"""
    try:
        # الحصول على بيانات الطلب كاملة
        conn = sqlite3.connect(DB_NAME)
        conn.execute('PRAGMA foreign_keys = ON')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE wasl_number = ?', (wasl_number,))
        order_data = cursor.fetchone()
        
        if order_data:
            # إنشاء جدول الأرشيف إذا لم يكن موجوداً
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS deleted_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_id INTEGER,
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
                    deleted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    deleted_by TEXT DEFAULT 'system'
                )
            ''')
            
            # نسخ الطلب إلى أرشيف المحذوفات
            # order_data structure: (id, customer_id, wasl_number, order_number, customer_name,
            #                       mandob_name, city, area, customer_phone, total_amount, 
            #                       delivery_fee, net_amount, status, add_date, print_date, 
            #                       added_by, created_at)
            cursor.execute('''
                INSERT INTO deleted_orders (
                    original_id, customer_id, wasl_number, order_number, customer_name,
                    mandob_name, city, area, customer_phone, total_amount, delivery_fee,
                    net_amount, status, add_date, print_date, added_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_data[0], order_data[1], order_data[2], order_data[3], order_data[4],
                  order_data[5], order_data[6], order_data[7], order_data[8], order_data[9],
                  order_data[10], order_data[11], order_data[12], order_data[13], order_data[14],
                  order_data[15]))
            
            # حذف الطلب من الجدول الأساسي
            cursor.execute('DELETE FROM orders WHERE wasl_number = ?', (wasl_number,))
            
            # حذف السجلات المرتبطة من جداول أخرى
            cursor.execute('DELETE FROM order_monitoring WHERE wasl_number = ?', (wasl_number,))
            cursor.execute('DELETE FROM isolated_orders WHERE wasl_number = ?', (wasl_number,))
            cursor.execute('DELETE FROM processed_orders WHERE wasl_number = ?', (wasl_number,))
            
            conn.commit()
            conn.close()
            
            order_number = order_data[3]  # order_number هو العمود الرابع
            
            # فتح رابط الحذف في الخلفية
            import threading
            def delete_from_external_system():
                try:
        import webbrowser
                    url = f"https://alkarar-exp.com/manage_newwasl.php?wasl_id={order_number}"
                    webbrowser.open(url, new=2, autoraise=False)
                    print(f"✅ تم فتح رابط الحذف للوصل {wasl_number} (طلب {order_number})")
                except Exception as e:
                    print(f"❌ خطأ في فتح رابط الحذف: {e}")
            
            # تشغيل الحذف الخارجي في الخلفية
            delete_thread = threading.Thread(target=delete_from_external_system)
            delete_thread.daemon = True
            delete_thread.start()
            
            flash(f'تم حذف الطلب رقم {wasl_number} من قاعدة البيانات ونقله إلى أرشيف المحذوفات. جاري حذفه من النظام الخارجي في الخلفية.', 'success')
        else:
            flash(f'لم يتم العثور على الطلب برقم الوصل {wasl_number}', 'error')
    except Exception as e:
        flash(f'خطأ في حذف الطلب: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('index'))

@app.route('/print_suspended_report')
def print_suspended_report():
    """إنشاء تقرير طباعة A4 للطلبات المعلقة"""
    db = DatabaseManager()
    orders = db.get_suspended_orders()

    # الحصول على التاريخ الحالي بالتنسيق العربي
    from datetime import datetime

    # أسماء الأشهر بالعربي
    arabic_months = [
        '', 'كانون الثاني', 'شباط', 'آذار', 'نيسان', 'أيار', 'حزيران',
        'تموز', 'آب', 'أيلول', 'تشرين الأول', 'تشرين الثاني', 'كانون الأول'
    ]
    
    # أسماء الأيام بالعربي
    arabic_weekdays = [
        'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد'
    ]
    
    now = datetime.now()
    day = str(now.day)
    month = arabic_months[now.month]
    year = str(now.year)
    weekday = arabic_weekdays[now.weekday()]
    
    # تحويل الأرقام إلى أرقام عربية
    def to_arabic_numbers(s):
        return s.translate(str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩'))
    
    current_date = f"{weekday} {to_arabic_numbers(day)} {month} {to_arabic_numbers(year)}"
    current_time = f"{to_arabic_numbers(now.strftime('%H:%M'))}"
    current_year = year
    
    # إحصائيات التقرير
    status_stats = {}
    city_stats = {}
    total_amount = 0
    
    for order in orders:
        # إحصائيات الحالات
        status = order['status']
        status_stats[status] = status_stats.get(status, 0) + 1
        
        # إحصائيات المدن
        city = order['city']
        city_stats[city] = city_stats.get(city, 0) + 1
        
        # المجموع الكلي
        total_amount += order['total_amount'] or 0

    return render_template('print_suspended_report.html', 
                         orders=orders, 
                         current_date=current_date,
                         current_time=current_time,
                         current_year=current_year,
                         total_orders=len(orders),
                         status_stats=status_stats,
                         city_stats=city_stats,
                         total_amount=total_amount)

@app.route('/mark_isolated_processed', methods=['POST'])
def mark_isolated_processed():
    """تمييز الطلب المعزول كمعالج"""
    try:
        data = request.get_json()
        wasl_number = data.get('wasl_number')
        
        if not wasl_number:
            return jsonify({'success': False, 'error': 'رقم الوصل مطلوب'})
        
        db = DatabaseManager()
        success = db.mark_isolated_order_processed(wasl_number)
        
        if success:
            return jsonify({'success': True, 'message': 'تم تمييز الطلب كمعالج بنجاح'})
        else:
            return jsonify({'success': False, 'error': 'لم يتم العثور على الطلب أو حدث خطأ في التحديث'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/processed_orders')
def processed_orders():
    """صفحة الطلبات المعالجة"""
    db = DatabaseManager()
    orders = db.get_processed_orders()
    return render_template('processed_orders.html', orders=orders)

@app.route('/deleted_orders')
def deleted_orders():
    """صفحة أرشيف الطلبات المحذوفة"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # إنشاء الجدول إذا لم يكن موجوداً
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deleted_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_id INTEGER,
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
                deleted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                deleted_by TEXT DEFAULT 'system'
            )
        ''')
        
        # جلب الطلبات المحذوفة
        cursor.execute('''
            SELECT * FROM deleted_orders 
            ORDER BY deleted_at DESC
        ''')
        
        orders = []
        for row in cursor.fetchall():
            orders.append({
                'id': row[0],
                'original_id': row[1],
                'customer_id': row[2],
                'wasl_number': row[3],
                'order_number': row[4],
                'customer_name': row[5],
                'mandob_name': row[6],
                'city': row[7],
                'area': row[8],
                'customer_phone': row[9],
                'total_amount': row[10] or 0,
                'delivery_fee': row[11] or 0,
                'net_amount': row[12] or 0,
                'status': row[13],
                'add_date': row[14],
                'print_date': row[15],
                'added_by': row[16],
                'deleted_at': row[17],
                'deleted_by': row[18]
            })
        
        conn.close()
        return render_template('deleted_orders.html', orders=orders)
        
    except Exception as e:
        flash(f'خطأ في جلب الطلبات المحذوفة: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/restore_order/<int:deleted_order_id>', methods=['POST'])
def restore_order(deleted_order_id):
    """استعادة طلب محذوف"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # جلب بيانات الطلب المحذوف
        cursor.execute('SELECT * FROM deleted_orders WHERE id = ?', (deleted_order_id,))
        deleted_order = cursor.fetchone()
        
        if deleted_order:
            # التحقق من عدم وجود طلب بنفس رقم الوصل
            cursor.execute('SELECT id FROM orders WHERE wasl_number = ?', (deleted_order[3],))
            if cursor.fetchone():
                flash(f'يوجد طلب بنفس رقم الوصل {deleted_order[3]} في النظام', 'error')
                conn.close()
                return redirect(url_for('deleted_orders'))
            
            # استعادة الطلب إلى الجدول الأساسي
            cursor.execute('''
                INSERT INTO orders (
                    customer_id, wasl_number, order_number, customer_name,
                    mandob_name, city, area, customer_phone, total_amount,
                    delivery_fee, net_amount, status, add_date, print_date, added_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', deleted_order[2:17])  # تجاهل id و original_id
            
            # حذف الطلب من أرشيف المحذوفات
            cursor.execute('DELETE FROM deleted_orders WHERE id = ?', (deleted_order_id,))
            
            conn.commit()
            conn.close()
            
            flash(f'تم استعادة الطلب رقم {deleted_order[3]} بنجاح', 'success')
        else:
            flash('لم يتم العثور على الطلب المحذوف', 'error')
            
    except Exception as e:
        flash(f'خطأ في استعادة الطلب: {str(e)}', 'error')
    
    return redirect(url_for('deleted_orders'))

@app.route('/clean_duplicate_data', methods=['POST'])
def clean_duplicate_data():
    """تنظيف البيانات المكررة في قاعدة البيانات"""
    try:
        session_id = '9d427774521140c6f62c431743d91572'
        monitor = OrderMonitor(session_id)
        
        if monitor.create_connection():
            # تنظيف البيانات المكررة
            success = monitor.clean_duplicate_data()
            
            if success:
                # مزامنة جدول التحقق من التفرد
                monitor.sync_unique_check_table()
                
                # الحصول على إحصائيات التكرار
                duplicate_stats = monitor.get_duplicate_statistics()
                
                monitor.close_connection()
                
                flash(f'تم تنظيف البيانات المكررة بنجاح!', 'success')
                
                if duplicate_stats:
                    flash(f'تم حذف {duplicate_stats["orders"]["duplicates"]} طلب مكرر', 'info')
                    flash(f'تم حذف {duplicate_stats["monitoring"]["duplicates"]} تغيير مكرر', 'info')
                    flash(f'تم حذف {duplicate_stats["isolated"]["duplicates"]} طلب معزول مكرر', 'info')
            else:
                flash('فشل في تنظيف البيانات المكررة', 'error')
        else:
            flash('فشل في الاتصال بقاعدة البيانات', 'error')
    except Exception as e:
        flash(f'خطأ في تنظيف البيانات: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/duplicate_statistics')
def duplicate_statistics():
    """عرض إحصائيات التكرار في قاعدة البيانات"""
    try:
        session_id = '9d427774521140c6f62c431743d91572'
        monitor = OrderMonitor(session_id)
        
        if monitor.create_connection():
            duplicate_stats = monitor.get_duplicate_statistics()
            monitor.close_connection()
            
            return jsonify({
                'success': True,
                'data': duplicate_stats
            })
        else:
            return jsonify({
                'success': False,
                'error': 'فشل في الاتصال بقاعدة البيانات'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/sync_unique_check', methods=['POST'])
def sync_unique_check():
    """مزامنة جدول التحقق من التفرد"""
    try:
        session_id = '9d427774521140c6f62c431743d91572'
        monitor = OrderMonitor(session_id)
        
        if monitor.create_connection():
            success = monitor.sync_unique_check_table()
            
            if success:
                monitor.close_connection()
                flash('تم مزامنة جدول التحقق من التفرد بنجاح!', 'success')
            else:
                flash('فشل في مزامنة جدول التحقق من التفرد', 'error')
        else:
            flash('فشل في الاتصال بقاعدة البيانات', 'error')
    except Exception as e:
        flash(f'خطأ في المزامنة: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/database_health')
def database_health():
    """فحص صحة قاعدة البيانات ومنع التكرار"""
    try:
        session_id = '9d427774521140c6f62c431743d91572'
        monitor = OrderMonitor(session_id)
        
        if monitor.create_connection():
            # الحصول على إحصائيات التكرار
            duplicate_stats = monitor.get_duplicate_statistics()
            
            # الحصول على إحصائيات المراقبة
            monitoring_stats = monitor.get_monitoring_stats()
            
            monitor.close_connection()
            
            return jsonify({
                'success': True,
                'duplicate_stats': duplicate_stats,
                'monitoring_stats': monitoring_stats,
                'health_status': 'healthy'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'فشل في الاتصال بقاعدة البيانات',
                'health_status': 'unhealthy'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'health_status': 'unhealthy'
        })

def start_background_monitoring():
    """تشغيل المراقبة في الخلفية - تنزيل فوري ومستمر مع منع التكرار"""
    global monitoring_active, monitoring_threads
    
    def run_monitoring():
        global monitoring_active
        monitoring_active = True
        
        session_id = '9d427774521140c6f62c431743d91572'
        
        # حساب التواريخ تلقائياً - من غد إلى قبل شهر بالضبط
        from datetime import datetime, timedelta
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        one_month_ago = today - timedelta(days=30)
        
        # تنسيق التواريخ بالشكل الأمريكي MM/DD/YYYY
        end_date = tomorrow.strftime('%m/%d/%Y')
        start_date = one_month_ago.strftime('%m/%d/%Y')
        
        print(f"📅 الفترة التلقائية: من {start_date} إلى {end_date}")
        print(f"🚀 بدء المراقبة التلقائية المحسنة - تنزيل فوري مع منع التكرار")
        
        # إعداد أولي لقاعدة البيانات
        try:
            monitor = OrderMonitor(session_id)
            if monitor.create_connection():
                print("🔧 إعداد قاعدة البيانات...")
                
                # مزامنة جدول التحقق من التفرد
                monitor.sync_unique_check_table()
                
                # تنظيف البيانات المكررة
                monitor.clean_duplicate_data()
                
                monitor.close_connection()
                print("✅ تم إعداد قاعدة البيانات بنجاح")
            else:
                print("❌ فشل في إعداد قاعدة البيانات")
        except Exception as e:
            print(f"❌ خطأ في إعداد قاعدة البيانات: {e}")
        
        # حلقة لإعادة التشغيل التلقائي عند حدوث أخطاء
        while monitoring_active:
            try:
                monitor = OrderMonitor(session_id)
                if monitor.create_connection():
                    # تنزيل فوري - مراقبة كل ثانية واحدة مع منع التكرار
                    monitor.monitor_orders(start_date, end_date, interval_seconds=1)
                else:
                    print("❌ فشل في الاتصال بقاعدة البيانات، إعادة المحاولة...")
                    time.sleep(10)
            except Exception as e:
                print(f"❌ خطأ في المراقبة: {e}")
                print("🔄 إعادة تشغيل المراقبة تلقائياً بعد 10 ثوانٍ...")
                time.sleep(10)
    
    # تشغيل المراقبة في خيط منفصل
    thread = threading.Thread(target=run_monitoring)
    thread.daemon = True
    thread.start()
    
    monitoring_threads.append(thread)
    
    print("✅ تم بدء المراقبة التلقائية المستمرة مع منع التكرار في الخلفية")

@app.route('/start_realtime_monitoring', methods=['POST'])
def start_realtime_monitoring():
    """تشغيل المراقبة المباشرة المكثفة"""
    try:
        def run_intensive_monitoring():
            session_id = '9d427774521140c6f62c431743d91572'
            
            from datetime import datetime, timedelta
            today = datetime.now()
            tomorrow = today + timedelta(days=1)
            one_month_ago = today - timedelta(days=30)
            
            end_date = tomorrow.strftime('%m/%d/%Y')
            start_date = one_month_ago.strftime('%m/%d/%Y')
            
            print(f"🚀 بدء المراقبة المباشرة المكثفة - كل 0.5 ثانية")
            
            while True:
                try:
                    monitor = OrderMonitor(session_id)
                    if monitor.create_connection():
                        # مراقبة مكثفة كل نصف ثانية
                        monitor.monitor_orders(start_date, end_date, interval_seconds=0.5)
                    else:
                        print("❌ فشل في الاتصال، إعادة المحاولة...")
                        time.sleep(5)
                except Exception as e:
                    print(f"❌ خطأ في المراقبة المكثفة: {e}")
                    time.sleep(5)
        
        thread = threading.Thread(target=run_intensive_monitoring)
        thread.daemon = True
        thread.start()
        
        flash('تم بدء المراقبة المباشرة المكثفة!', 'success')
    except Exception as e:
        flash(f'خطأ في بدء المراقبة المكثفة: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/start_ultra_fast_monitoring', methods=['POST'])
def start_ultra_fast_monitoring():
    """تشغيل المراقبة الفائقة السرعة"""
    global monitoring_active, monitoring_threads
    
    try:
        def run_ultra_fast_monitoring():
            global monitoring_active
            monitoring_active = True
            
            session_id = '9d427774521140c6f62c431743d91572'
            
            from datetime import datetime, timedelta
            today = datetime.now()
            tomorrow = today + timedelta(days=1)
            one_month_ago = today - timedelta(days=30)
            
            end_date = tomorrow.strftime('%m/%d/%Y')
            start_date = one_month_ago.strftime('%m/%d/%Y')
            
            print(f"🚀🚀 بدء المراقبة الفائقة السرعة - كل 0.1 ثانية")
            
            while monitoring_active:
                try:
                    monitor = OrderMonitor(session_id)
                    if monitor.create_connection():
                        # مراقبة فائقة السرعة كل عُشر ثانية
                        monitor.monitor_orders_ultra_fast(start_date, end_date, interval_seconds=0.1)
                    else:
                        print("❌ فشل في الاتصال، إعادة المحاولة...")
                        time.sleep(2)
                except Exception as e:
                    print(f"❌ خطأ في المراقبة الفائقة: {e}")
                    time.sleep(2)
            
            print("🛑 تم إيقاف المراقبة الفائقة السرعة")
        
        thread = threading.Thread(target=run_ultra_fast_monitoring)
        thread.daemon = True
        thread.start()
        
        monitoring_threads.append(thread)
        
        flash('تم بدء المراقبة الفائقة السرعة! (تنزيل كل 0.1 ثانية)', 'success')
    except Exception as e:
        flash(f'خطأ في بدء المراقبة الفائقة: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/stop_monitoring', methods=['POST'])
def stop_monitoring():
    """إيقاف جميع عمليات المراقبة"""
    global monitoring_active, monitoring_threads
    
    try:
        monitoring_active = False
        print("🛑 إيقاف جميع عمليات المراقبة...")
        
        # انتظار انتهاء الخيوط (مع timeout)
        for thread in monitoring_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        monitoring_threads.clear()
        
        flash('تم إيقاف جميع عمليات المراقبة بنجاح!', 'info')
    except Exception as e:
        flash(f'خطأ في إيقاف المراقبة: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/monitoring_status')
def monitoring_status():
    """التحقق من حالة المراقبة"""
    global monitoring_active, monitoring_threads
    
    active_threads = len([t for t in monitoring_threads if t.is_alive()])
    
    return jsonify({
        'monitoring_active': monitoring_active,
        'active_threads': active_threads,
        'total_threads': len(monitoring_threads)
    })

@app.route('/add_customer', methods=['POST'])
def add_customer():
    """إضافة عميل جديد"""
    try:
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({'success': False, 'error': 'اسم العميل مطلوب'})
        
        customer_name = data['name'].strip()
        customer_id = data.get('id', '').strip() if data.get('id') else None
        customer_phone = data.get('phone', '').strip() if data.get('phone') else None
        customer_address = data.get('address', '').strip() if data.get('address') else None
        
        # التحقق من صحة البيانات
        if len(customer_name) < 2:
            return jsonify({'success': False, 'error': 'اسم العميل يجب أن يحتوي على حرفين على الأقل'})
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # التحقق من عدم وجود عميل بنفس الاسم
        cursor.execute('SELECT id FROM customers WHERE name = ?', (customer_name,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'يوجد عميل بهذا الاسم مسبقاً'})
        
        # التحقق من المعرف المخصص إذا تم تقديمه
        if customer_id:
            cursor.execute('SELECT id FROM customers WHERE id = ?', (customer_id,))
            if cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'error': 'معرف العميل مستخدم مسبقاً'})
        
        # التأكد من وجود الأعمدة الجديدة
        try:
            cursor.execute("ALTER TABLE customers ADD COLUMN phone TEXT")
        except sqlite3.OperationalError:
            pass  # العمود موجود بالفعل
        
        try:
            cursor.execute("ALTER TABLE customers ADD COLUMN address TEXT")
        except sqlite3.OperationalError:
            pass  # العمود موجود بالفعل
        
        # إدراج العميل الجديد
        if customer_id:
            cursor.execute('''
                INSERT INTO customers (id, name, phone, address, created_at) 
                VALUES (?, ?, ?, ?, datetime('now'))
            ''', (customer_id, customer_name, customer_phone, customer_address))
        else:
            cursor.execute('''
                INSERT INTO customers (name, phone, address, created_at) 
                VALUES (?, ?, ?, datetime('now'))
            ''', (customer_name, customer_phone, customer_address))
            customer_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        # البحث التلقائي عن طلبات العميل الجديد
        try:
            from test import CustomerOrdersSearch
            from datetime import datetime, timedelta
            
            # إعداد التواريخ للبحث (آخر شهر)
            today = datetime.now()
            tomorrow = today + timedelta(days=1)
            one_month_ago = today - timedelta(days=30)
            
            end_date = tomorrow.strftime('%m/%d/%Y')
            start_date = one_month_ago.strftime('%m/%d/%Y')
            
            session_id = '9d427774521140c6f62c431743d91572'  # معرف الجلسة - تأكد من أنه محدث
            searcher = CustomerOrdersSearch(session_id)
            
            # إضافة العميل الجديد لقائمة العملاء إذا لم يكن موجوداً
            existing_customer = next((c for c in searcher.customers if c['id'] == customer_id), None)
            if not existing_customer:
                searcher.customers.append({'id': customer_id, 'name': customer_name})
                print(f"➕ تم إضافة العميل الجديد لقائمة البحث: {customer_name} (ID: {customer_id})")
            
            # البحث عن طلبات العميل الجديد
            print(f"🔍 البحث عن طلبات العميل الجديد: {customer_name} (ID: {customer_id})")
            print(f"📅 من {start_date} إلى {end_date}")
            
            # تشغيل البحث في خيط منفصل لعدم تأخير الاستجابة
            import threading
            def search_new_customer():
                try:
                    result = searcher.search_customer_orders(customer_id, customer_name, start_date, end_date)
                    print(f"✅ تم البحث عن طلبات العميل: {customer_name} - عدد الطلبات: {result['total_orders']}")
                    
                    # حفظ النتائج في قاعدة البيانات
                    if result['total_orders'] > 0:
                        success = save_customer_orders_to_db(result)
                        if success:
                            print(f"💾 تم حفظ {result['total_orders']} طلب للعميل {customer_name}")
                        else:
                            print(f"❌ فشل في حفظ طلبات العميل {customer_name}")
                    else:
                        print(f"📭 لم يتم العثور على طلبات للعميل {customer_name} في الفترة المحددة")
                    
                except Exception as e:
                    print(f"❌ خطأ في البحث عن طلبات العميل {customer_name}: {e}")
            
            search_thread = threading.Thread(target=search_new_customer)
            search_thread.daemon = True
            search_thread.start()
            
        except Exception as e:
            print(f"⚠️ تحذير: لم يتم البحث عن طلبات العميل الجديد: {e}")
        
        return jsonify({
            'success': True, 
            'message': 'تم إضافة العميل بنجاح وبدء البحث عن طلباته',
            'customer_id': customer_id,
            'customer_name': customer_name,
            'search_started': True
        })
        
    except Exception as e:
        print(f"خطأ في إضافة العميل: {e}")
        return jsonify({'success': False, 'error': 'حدث خطأ في الخادم'})

def save_customer_orders_to_db(result):
    """حفظ طلبات العميل في قاعدة البيانات"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        customer_id = result['customer_id']
        saved_orders = 0
        skipped_orders = 0
        
        for order in result['orders']:
            try:
                # تحويل المبالغ إلى أرقام
                total_amount = float(order['total_amount'].replace(',', '')) if order['total_amount'] and order['total_amount'] != '0' else 0.0
                delivery_fee = float(order['delivery_fee'].replace(',', '')) if order['delivery_fee'] and order['delivery_fee'] != '0' else 0.0
                net_amount = float(order['net_amount'].replace(',', '')) if order['net_amount'] and order['net_amount'] != '0' else 0.0
                
                # التحقق من عدم وجود الطلب مسبقاً
                cursor.execute('SELECT id FROM orders WHERE wasl_number = ?', (order['wasl_number'],))
                if cursor.fetchone():
                    skipped_orders += 1
                    continue  # الطلب موجود مسبقاً
                
                cursor.execute('''
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
                saved_orders += 1
                
            except Exception as e:
                print(f"خطأ في حفظ الطلب {order.get('wasl_number', 'غير محدد')}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        if saved_orders > 0:
            print(f"✅ تم حفظ {saved_orders} طلب جديد")
        if skipped_orders > 0:
            print(f"⏭️ تم تجاهل {skipped_orders} طلب موجود مسبقاً")
            
        return saved_orders > 0
        
    except Exception as e:
        print(f"❌ خطأ في حفظ طلبات العميل: {e}")
        return False

@app.route('/search_customer_orders', methods=['POST'])
def search_customer_orders():
    """البحث عن طلبات عميل محدد"""
    try:
        data = request.get_json()
        
        if not data or not data.get('customer_id'):
            return jsonify({'success': False, 'error': 'معرف العميل مطلوب'})
        
        customer_id = data['customer_id']
        customer_name = data.get('customer_name', f'العميل {customer_id}')
        
        print(f"🔍 بدء البحث عن طلبات العميل: {customer_name} (ID: {customer_id})")
        
        # تشغيل البحث في خيط منفصل
        import threading
        def search_customer():
            try:
                from test import CustomerOrdersSearch
                from datetime import datetime, timedelta
                
                # إعداد التواريخ للبحث (آخر شهر)
                today = datetime.now()
                tomorrow = today + timedelta(days=1)
                one_month_ago = today - timedelta(days=30)
                
                end_date = tomorrow.strftime('%m/%d/%Y')
                start_date = one_month_ago.strftime('%m/%d/%Y')
                
                session_id = '9d427774521140c6f62c431743d91572'  # معرف الجلسة
                searcher = CustomerOrdersSearch(session_id)
                
                # إضافة العميل لقائمة العملاء إذا لم يكن موجوداً
                existing_customer = next((c for c in searcher.customers if c['id'] == customer_id), None)
                if not existing_customer:
                    searcher.customers.append({'id': customer_id, 'name': customer_name})
                    print(f"➕ تم إضافة العميل لقائمة البحث: {customer_name} (ID: {customer_id})")
                
                result = searcher.search_customer_orders(customer_id, customer_name, start_date, end_date)
                print(f"✅ تم البحث عن طلبات العميل: {customer_name} - عدد الطلبات: {result['total_orders']}")
                
                # حفظ النتائج في قاعدة البيانات
                if result['total_orders'] > 0:
                    success = save_customer_orders_to_db(result)
                    if success:
                        print(f"💾 تم حفظ {result['total_orders']} طلب للعميل {customer_name}")
                    else:
                        print(f"❌ فشل في حفظ طلبات العميل {customer_name}")
                else:
                    print(f"📭 لم يتم العثور على طلبات للعميل {customer_name} في الفترة المحددة")
                    
            except Exception as e:
                print(f"❌ خطأ في البحث عن طلبات العميل {customer_name}: {e}")
        
        search_thread = threading.Thread(target=search_customer)
        search_thread.daemon = True
        search_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'تم بدء البحث عن طلبات العميل: {customer_name}',
            'customer_id': customer_id,
            'customer_name': customer_name
        })
        
    except Exception as e:
        print(f"خطأ في البحث عن طلبات العميل: {e}")
        return jsonify({'success': False, 'error': 'حدث خطأ في الخادم'})

if __name__ == '__main__':
    # بدء المراقبة التلقائية
    start_background_monitoring()
    
    # تشغيل الموقع
    app.run(debug=True, host='0.0.0.0', port=5000) 