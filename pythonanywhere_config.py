#!/usr/bin/env python3
"""
إعدادات خاصة لـ PythonAnywhere
PythonAnywhere specific configuration
"""

import os
import sys

# إعدادات PythonAnywhere
PYTHONANYWHERE_MODE = True

# إعدادات قاعدة البيانات
DATABASE_PATH = '/home/yourusername/SP-EYE1/customer_orders.db'

# إعدادات التطبيق
DEBUG_MODE = False
SECRET_KEY = 'your-secret-key-here'

# إعدادات المراقبة
MONITORING_ENABLED = True
MONITORING_INTERVAL = 60  # ثانية

# إعدادات الأمان
DISABLE_SUBPROCESS = True
DISABLE_WEBBROWSER = True

# إعدادات التسجيل
LOGGING_ENABLED = True
LOG_LEVEL = 'INFO'

# إعدادات الجلسة
SESSION_ID = '9d427774521140c6f62c431743d91572'

# معلومات الاتصال بالنظام الخارجي
EXTERNAL_SYSTEM_URL = 'https://alkarar-exp.com'

# إعدادات الذاكرة والأداء
MAX_WORKERS = 2
THREAD_POOL_SIZE = 4

def get_config():
    """إرجاع إعدادات التطبيق"""
    return {
        'PYTHONANYWHERE_MODE': PYTHONANYWHERE_MODE,
        'DATABASE_PATH': DATABASE_PATH,
        'DEBUG_MODE': DEBUG_MODE,
        'SECRET_KEY': SECRET_KEY,
        'MONITORING_ENABLED': MONITORING_ENABLED,
        'MONITORING_INTERVAL': MONITORING_INTERVAL,
        'DISABLE_SUBPROCESS': DISABLE_SUBPROCESS,
        'DISABLE_WEBBROWSER': DISABLE_WEBBROWSER,
        'LOGGING_ENABLED': LOGGING_ENABLED,
        'LOG_LEVEL': LOG_LEVEL,
        'SESSION_ID': SESSION_ID,
        'EXTERNAL_SYSTEM_URL': EXTERNAL_SYSTEM_URL,
        'MAX_WORKERS': MAX_WORKERS,
        'THREAD_POOL_SIZE': THREAD_POOL_SIZE
    }

def is_pythonanywhere():
    """فحص ما إذا كان التطبيق يعمل على PythonAnywhere"""
    return 'pythonanywhere' in os.environ.get('SERVER_SOFTWARE', '').lower() or \
           'pythonanywhere' in os.getcwd().lower() or \
           PYTHONANYWHERE_MODE

def setup_pythonanywhere_environment():
    """إعداد البيئة لـ PythonAnywhere"""
    if is_pythonanywhere():
        # إضافة مسار المشروع إلى sys.path
        project_path = os.path.dirname(os.path.abspath(__file__))
        if project_path not in sys.path:
            sys.path.insert(0, project_path)
        
        # إعداد متغيرات البيئة
        os.environ['FLASK_ENV'] = 'production'
        os.environ['PYTHONANYWHERE_MODE'] = 'true'
        
        print("✅ تم إعداد البيئة لـ PythonAnywhere")
        return True
    return False 