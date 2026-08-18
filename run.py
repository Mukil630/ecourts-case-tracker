import os
from app import create_app
from app.config import DevelopmentConfig

app = create_app(DevelopmentConfig())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 eCourts Case Tracker Development Server starting on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
