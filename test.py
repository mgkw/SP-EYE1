#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import json
import csv
from datetime import datetime, timedelta
import time
import sys
from create_database import CustomerOrdersDatabase
from monitor_orders import OrderMonitor

class CustomerOrdersSearch:
    def __init__(self, session_id):
        self.session_id = session_id
        self.base_url = 'https://alkarar-exp.com/'
        
        # إعداد الجلسة
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
        
        # تعيين الكوكي
        self.session.cookies.set('PHPSESSID', session_id, domain='alkarar-exp.com')
        
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
            {'id': 194, 'name': 'سابوي'}
        ]

    def format_date(self, date_obj):
        """تحويل التاريخ إلى التنسيق المطلوب DD/MM/YYYY"""
        return date_obj.strftime('%d/%m/%Y')

    def search_customer_orders(self, customer_id, customer_name, start_date, end_date):
        """البحث عن طلبات عميل محدد"""
        try:
            print(f"🔍 البحث عن طلبات العميل: {customer_name} (ID: {customer_id})")
            print(f"📅 من: {start_date} إلى: {end_date}")

            # تجهيز بيانات البحث باستخدام multipart/form-data
            data = {
                'city': '',
                'date_add': start_date,  # تاريخ البداية
                'to_date_add': end_date,  # تاريخ النهاية
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

            # إرسال طلب البحث إلى /search_wasl.php
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
                }
            )

            # تحليل النتائج
            orders = self.parse_orders_table(response.text)
            
            print(f"✅ تم العثور على {len(orders)} طلب للعميل {customer_name}")
            
            return {
                'customer_id': customer_id,
                'customer_name': customer_name,
                'start_date': start_date,
                'end_date': end_date,
                'orders': orders,
                'total_orders': len(orders)
            }

        except Exception as error:
            print(f"❌ خطأ في البحث عن طلبات {customer_name}: {str(error)}")
            if hasattr(error, 'response'):
                print(f"📊 رمز الاستجابة: {error.response.status_code}")
            return {
                'customer_id': customer_id,
                'customer_name': customer_name,
                'start_date': start_date,
                'end_date': end_date,
                'orders': [],
                'total_orders': 0,
                'error': str(error)
            }

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
            if len(cells) > 10:  # تأكد من أن الصف يحتوي على بيانات
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

    def search_all_customers(self, start_date, end_date):
        """البحث عن جميع العملاء"""
        start_date_formatted = start_date
        end_date_formatted = end_date
        
        print("🚀 بدء البحث عن طلبات جميع العملاء")
        print(f"📅 الفترة: من {start_date} إلى {end_date_formatted}")
        print("=" * 60)

        results = []
        total_orders = 0

        for customer in self.customers:
            result = self.search_customer_orders(
                customer['id'],
                customer['name'],
                start_date,
                end_date_formatted
            )
            
            results.append(result)
            total_orders += result['total_orders']
            
            # انتظار قليل بين الطلبات
            time.sleep(1)

        # طباعة ملخص النتائج
        self.print_summary(results, total_orders, start_date, end_date_formatted)
        
        return {
            'period': {'start': start_date, 'end': end_date_formatted},
            'results': results,
            'total_orders': total_orders
        }

    def search_single_customer(self, customer_id, customer_name, end_date):
        """البحث عن وكيل واحد فقط"""
        end_date_obj = datetime.strptime(end_date, '%d/%m/%Y')
        start_date_obj = end_date_obj - timedelta(days=30)
        
        start_date = self.format_date(start_date_obj)
        end_date_formatted = self.format_date(end_date_obj)
        
        print("🚀 بدء البحث عن طلبات وكيل واحد")
        print(f"👤 الوكيل: {customer_name} (ID: {customer_id})")
        print(f"📅 الفترة: من {start_date} إلى {end_date_formatted}")
        print("=" * 60)

        result = self.search_customer_orders(
            customer_id,
            customer_name,
            start_date,
            end_date_formatted
        )

        # طباعة ملخص النتائج
        self.print_single_customer_summary(result, start_date, end_date_formatted)
        
        return {
            'period': {'start': start_date, 'end': end_date_formatted},
            'customer': result
        }

    def print_single_customer_summary(self, result, start_date, end_date):
        """طباعة ملخص لوكيل واحد"""
        print("\n📊 ملخص النتائج:")
        print("=" * 40)
        print(f"👤 الوكيل: {result['customer_name']}")
        print(f"📅 الفترة: {start_date} - {end_date}")
        print(f"📦 عدد الطلبات: {result['total_orders']}")
        
        if 'error' in result:
            print(f"❌ خطأ: {result['error']}")
        elif result['total_orders'] > 0:
            print("\n📋 تفاصيل الطلبات:")
            for i, order in enumerate(result['orders'], 1):
                print(f"{i}. رقم الوصل: {order['wasl_number']} | المبلغ: {order['total_amount']} | الحالة: {order['status']}")
        else:
            print("📭 لا توجد طلبات في هذه الفترة")

    def print_summary(self, results, total_orders, start_date, end_date):
        """طباعة ملخص النتائج"""
        print("\n📊 ملخص النتائج:")
        print("=" * 40)
        print(f"📅 الفترة: {start_date} - {end_date}")
        print(f"👥 عدد العملاء: {len(results)}")
        print(f"📦 إجمالي الطلبات: {total_orders}")
        print("\n📋 تفاصيل العملاء:")
        
        for result in results:
            status = "❌" if 'error' in result else "✅"
            print(f"{status} {result['customer_name']}: {result['total_orders']} طلب")

    def show_available_customers(self):
        """عرض قائمة العملاء المتاحة"""
        print("\n👥 العملاء المتاحون:")
        print("=" * 30)
        for i, customer in enumerate(self.customers, 1):
            print(f"{i}. {customer['name']} (ID: {customer['id']})")

    def find_customer(self, search_term):
        """البحث عن وكيل بالاسم أو ID"""
        search_term = str(search_term).lower()
        
        # البحث بالاسم
        for customer in self.customers:
            if search_term in customer['name'].lower():
                return customer
        
        # البحث بالID
        for customer in self.customers:
            if str(customer['id']) == search_term:
                return customer
        
        return None

    def export_to_json(self, results, filename='customer_orders.json'):
        """تصدير النتائج إلى JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"💾 تم تصدير النتائج إلى: {filename}")

    def export_to_csv(self, results, filename='customer_orders.csv'):
        """تصدير النتائج إلى CSV"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Customer Name', 'Wasl Number', 'Order Number', 'Customer Phone', 'Total Amount', 'Status', 'Add Date'])
            
            if isinstance(results, list):
                for result in results:
                    if 'orders' in result and isinstance(result['orders'], list):
                        for order in result['orders']:
                            writer.writerow([
                                result['customer_name'],
                                order['wasl_number'],
                                order['order_number'],
                                order['customer_phone'],
                                order['total_amount'],
                                order['status'],
                                order['add_date']
                            ])
        
        print(f"💾 تم تصدير النتائج إلى: {filename}")

def main():
    session_id = '9d427774521140c6f62c431743d91572'  # استبدل بجلسة صحيحة
    
    # حساب التواريخ تلقائياً - من غد إلى قبل شهر بالضبط
    from datetime import datetime, timedelta
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    one_month_ago = today - timedelta(days=30)
    
    # تنسيق التواريخ بالشكل الأمريكي MM/DD/YYYY
    end_date = tomorrow.strftime('%m/%d/%Y')
    start_date = one_month_ago.strftime('%m/%d/%Y')
    
    print(f"📅 الفترة التلقائية: من {start_date} إلى {end_date}")
    
    searcher = CustomerOrdersSearch(session_id)
    
    try:
        print("🎯 بدء البحث عن طلبات جميع الوكلاء")
        print(f"📅 تاريخ النهاية: {end_date}")
        print("=" * 50)
        
        # عرض العملاء المتاحين
        searcher.show_available_customers()
        
        # البحث عن جميع الوكلاء
        print("\n🔍 البحث عن جميع الوكلاء...")
        results = searcher.search_all_customers(start_date, end_date)
        
        # تصدير النتائج
        filename = f"all_customers_orders_{end_date.replace('/', '-')}.json"
        # searcher.export_to_json(results, filename)
        # searcher.export_to_csv(results, filename.replace('.json', '.csv'))
        
        # حفظ النتائج في قاعدة البيانات مباشرة
        db = CustomerOrdersDatabase()
        if db.create_connection():
            db.create_tables()
            # قائمة العملاء نفسها المستخدمة في البحث
            customers = searcher.customers
            db.insert_customers(customers)
            # حفظ النتائج مباشرة بدون قراءة من ملف
            db.insert_orders(results, results['period'])
            db.create_indexes()
            db.get_statistics()
            db.close_connection()
        print("\n🏁 انتهى البحث بنجاح!")
        
        # بدء المراقبة المستمرة
        print("\n🔍 بدء المراقبة المستمرة...")
        monitor = OrderMonitor(session_id)
        if monitor.create_connection():
            try:
                monitor.monitor_orders(start_date, end_date, interval_seconds=5)
            except KeyboardInterrupt:
                print("\n⏹️  تم إيقاف المراقبة بواسطة المستخدم")
            finally:
                monitor.close_connection()
        
    except Exception as error:
        print(f"❌ خطأ في تشغيل البحث: {str(error)}")

if __name__ == "__main__":
    main() 