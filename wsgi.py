#!/usr/bin/env python3
"""
WSGI configuration for SP-EYE1 application on PythonAnywhere.

This module contains the WSGI application used by PythonAnywhere's
web servers to serve your application.
"""

import sys
import os

# Add your project directory to the sys.path
# Replace 'yourusername' with your actual PythonAnywhere username
# path = '/home/yourusername/SP-EYE1'
# if path not in sys.path:
#     sys.path.insert(0, path)

# Set the path to your project directory
project_home = '/home/yourusername/SP-EYE1'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import your Flask application
from app import app as application

if __name__ == "__main__":
    application.run(debug=False) 