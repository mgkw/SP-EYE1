#!/usr/bin/env python3
"""
WSGI configuration for SP-EYE1 application on PythonAnywhere.

This module contains the WSGI application used by PythonAnywhere's
web servers to serve your application.
"""

import sys
import os

# إعداد مسار المشروع
# استبدل 'yourusername' باسم المستخدم الخاص بك على PythonAnywhere
project_home = '/home/yourusername/SP-EYE1'

# إضافة مسار المشروع إلى sys.path
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# إعداد متغيرات البيئة
os.environ['FLASK_ENV'] = 'production'
os.environ['PYTHONANYWHERE_MODE'] = 'true'

# إعداد مسار قاعدة البيانات
os.environ['DATABASE_PATH'] = os.path.join(project_home, 'customer_orders.db')

try:
    # إعداد البيئة لـ PythonAnywhere
    from pythonanywhere_config import setup_pythonanywhere_environment
    setup_pythonanywhere_environment()
    
    # استيراد التطبيق
    from app import app as application
    
    print("✅ تم تحميل التطبيق بنجاح على PythonAnywhere")
    
except ImportError as e:
    print(f"❌ خطأ في استيراد التطبيق: {e}")
    # في حالة عدم وجود ملف pythonanywhere_config، استخدم الاستيراد المباشر
    from app import app as application
    
except Exception as e:
    print(f"❌ خطأ عام في تحميل التطبيق: {e}")
    raise

# للتأكد من أن التطبيق يعمل
if __name__ == "__main__":
    # هذا الجزء لن يتم تنفيذه على PythonAnywhere
    # ولكنه مفيد للاختبار المحلي
    print("🔧 تشغيل التطبيق في وضع التطوير...")
    application.run(debug=True)
