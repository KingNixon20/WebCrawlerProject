# wsgi.py
from app import app

if __name__ == "__main__":
    # Only used if you run `python wsgi.py` directly
    app.run(host="127.0.0.1", port=5000)
