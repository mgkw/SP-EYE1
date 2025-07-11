#!/bin/bash

echo "========================================"
echo "   سبونج إي - نظام مراقبة الطلبات"
echo "========================================"
echo

echo "[1/4] تثبيت المكتبات المطلوبة..."
pip install -r requirements.txt

echo
echo "[2/4] إنشاء قاعدة البيانات..."
python create_database.py

echo
echo "[3/4] تشغيل النظام..."
echo
echo "========================================"
echo "   النظام جاهز للاستخدام"
echo "   افتح المتصفح واذهب إلى:"
echo "   http://127.0.0.1:5000"
echo "========================================"
echo

python app.py 