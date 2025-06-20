# config.py
import os
DB_HOST = os.environ.get('DB_HOST', 'localhost') #assuming its on this pc
DB_PORT = os.environ.get('DB_PORT', 'the port of your database')
DB_NAME = os.environ.get('DB_NAME', 'database name')
DB_USER = os.environ.get('DB_USER', 'your username')
DB_PASS = os.environ.get('DB_PASS', 'your-password')
JWT_SECRET = 'your-32-bit-string-here'