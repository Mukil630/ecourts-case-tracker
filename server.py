import os
from wsgi import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Advocate Case Automation Web Server starting on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
