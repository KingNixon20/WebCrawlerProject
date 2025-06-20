# config.py
import os

THREADS = 2              
ENABLE_CRAWLER = True
ENABLE_BRUTEFORCER = True
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "NAME_GOES_HERE")
DB_USER = os.getenv("DB_USER", "USERNAME_HERE")
DB_PASS = os.getenv("DB_PASS", "PASSWORD_HERE")

# How many tags to generate per page
MIN_TAGS = int(os.getenv("MIN_TAGS", "40"))
MAX_TAGS = int(os.getenv("MAX_TAGS", "100"))

# Database configuration
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'NAME')
DB_USER = os.environ.get('DB_USER', 'USERNAME')
DB_PASS = os.environ.get('DB_PASS', 'PASSWORD -ALL SAME AS ABOVE')

# JWT Secret Key - CHANGE THIS IN PRODUCTION!
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-super-secure-secret-key-change-this-in-production')
