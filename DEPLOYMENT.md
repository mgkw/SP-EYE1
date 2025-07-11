# دليل النشر على PythonAnywhere
# PythonAnywhere Deployment Guide

## متطلبات النشر | Deployment Requirements

### حساب PythonAnywhere
- أنشئ حساب على [PythonAnywhere](https://www.pythonanywhere.com/)
- اختر الخطة المناسبة (يمكن البدء بالخطة المجانية للاختبار)

## خطوات النشر | Deployment Steps

### 1. رفع الكود | Upload Code

#### الطريقة الأولى: استخدام Git
```bash
# في وحدة التحكم (Console) على PythonAnywhere
cd ~
git clone https://github.com/mgkw/SP-EYE1.git
cd SP-EYE1
```

#### الطريقة الثانية: رفع الملفات يدوياً
- استخدم تبويب "Files" في PythonAnywhere
- ارفع جميع ملفات المشروع

### 2. تثبيت المتطلبات | Install Dependencies

```bash
# في وحدة التحكم
cd ~/SP-EYE1
pip3.10 install --user -r requirements.txt
```

### 3. إنشاء قاعدة البيانات | Create Database

```bash
python3.10 create_database.py
```

### 4. إعداد التطبيق الويب | Web App Setup

#### انتقل إلى تبويب "Web" في PythonAnywhere:

1. **إنشاء تطبيق ويب جديد**:
   - اضغط على "Add a new web app"
   - اختر "Manual configuration"
   - اختر "Python 3.10"

2. **إعداد WSGI**:
   - في قسم "Code", اضغط على "WSGI configuration file"
   - احذف المحتوى الموجود واستبدله بالكود التالي:

```python
#!/usr/bin/env python3

import sys
import os

# استبدل 'yourusername' باسم المستخدم الخاص بك
project_home = '/home/yourusername/SP-EYE1'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application

if __name__ == "__main__":
    application.run(debug=False)
```

3. **إعداد مجلد الملفات الثابتة**:
   - في قسم "Static files"
   - أضف:
     - URL: `/static/`
     - Directory: `/home/yourusername/SP-EYE1/static/`

### 5. إعداد المتغيرات | Environment Setup

#### تحديث مسار Python:
في قسم "Code" > "Source code":
```
/home/yourusername/SP-EYE1
```

#### إضافة مسار Python:
في قسم "Code" > "Working directory":
```
/home/yourusername/SP-EYE1
```

### 6. إعادة تشغيل التطبيق | Restart Application

- اضغط على الزر الأخضر "Reload yourusername.pythonanywhere.com"
- انتظر حتى يكتمل إعادة التشغيل

## الإعدادات المتقدمة | Advanced Configuration

### إعداد المراقبة التلقائية | Auto-Monitoring Setup

#### إنشاء مهمة مجدولة (للحسابات المدفوعة):
```bash
# في Tasks
python3.10 /home/yourusername/SP-EYE1/monitor_orders.py
```

### إعداد قاعدة البيانات | Database Configuration

#### للحسابات المدفوعة - استخدام MySQL:
1. أنشئ قاعدة بيانات MySQL من تبويب "Databases"
2. حدّث إعدادات الاتصال في `app.py`:

```python
# إعدادات MySQL
MYSQL_HOST = 'yourusername.mysql.pythonanywhere-services.com'
MYSQL_USER = 'yourusername'
MYSQL_PASSWORD = 'your_password'
MYSQL_DATABASE = 'yourusername$speye1'
```

### إعداد النطاق المخصص | Custom Domain Setup

#### للحسابات المدفوعة:
1. انتقل إلى تبويب "Web"
2. في قسم "Domain name", أضف النطاق المخصص
3. حدّث إعدادات DNS في مزود النطاق

## استكشاف الأخطاء | Troubleshooting

### مشاكل شائعة:

#### 1. خطأ في استيراد الوحدات
```bash
# تأكد من تثبيت المتطلبات
pip3.10 install --user flask requests beautifulsoup4 lxml
```

#### 2. خطأ في مسار الملفات
- تأكد من صحة مسار المشروع في WSGI
- تحقق من أن جميع الملفات موجودة

#### 3. خطأ في قاعدة البيانات
```bash
# إعادة إنشاء قاعدة البيانات
python3.10 create_database.py
```

#### 4. خطأ في الصلاحيات
```bash
# تحديث صلاحيات الملفات
chmod +x ~/SP-EYE1/*.py
```

### فحص السجلات | Log Checking

#### سجل الأخطاء:
- انتقل إلى تبويب "Web"
- اضغط على "Error log" لمشاهدة الأخطاء

#### سجل الخادم:
- انتقل إلى تبويب "Web"
- اضغط على "Server log" لمشاهدة سجل الخادم

## الصيانة | Maintenance

### تحديث التطبيق | Update Application

```bash
# سحب آخر التحديثات
cd ~/SP-EYE1
git pull origin main

# تثبيت متطلبات جديدة (إن وجدت)
pip3.10 install --user -r requirements.txt

# إعادة تشغيل التطبيق
# اضغط على "Reload" في تبويب Web
```

### النسخ الاحتياطي | Backup

#### نسخ احتياطي لقاعدة البيانات:
```bash
# SQLite
cp ~/SP-EYE1/customer_orders.db ~/SP-EYE1/backup_$(date +%Y%m%d).db

# MySQL
mysqldump -u yourusername -p yourusername$speye1 > backup_$(date +%Y%m%d).sql
```

## الأمان | Security

### إعدادات الأمان:
1. **تغيير كلمات المرور الافتراضية**
2. **تفعيل HTTPS** (للحسابات المدفوعة)
3. **تحديد الوصول للملفات الحساسة**

### متغيرات البيئة:
```python
# في app.py
import os
SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key')
```

## الدعم | Support

### موارد مفيدة:
- [وثائق PythonAnywhere](https://help.pythonanywhere.com/)
- [دليل Flask على PythonAnywhere](https://help.pythonanywhere.com/pages/Flask/)
- [منتدى PythonAnywhere](https://www.pythonanywhere.com/forums/)

### للمساعدة:
- استخدم نظام التذاكر في PythonAnywhere
- راجع سجلات الأخطاء أولاً
- تأكد من اتباع جميع الخطوات بالترتيب

---

**ملاحظة:** استبدل `yourusername` باسم المستخدم الفعلي الخاص بك على PythonAnywhere في جميع الأوامر والمسارات. 