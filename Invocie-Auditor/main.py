import subprocess
import sys
import time
from pathlib import Path

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    mock_erp_path = base_dir / "mock_erp" / "app.py"
    dashboard_path = base_dir / "ui" / "streamlit_app.py"

    print("=" * 60)
    print("🚀 Starting AI Invoice Auditor Environment")
    print("=" * 60)

    # 1️⃣ Start Mock ERP API
    print("📡 Launching Mock ERP API (http://localhost:8001)...")
    erp_process = subprocess.Popen([sys.executable, str(mock_erp_path)])

    # Wait a bit for ERP API to start
    time.sleep(3)

    # 2️⃣ Start Streamlit Dashboard
    print("🧠 Launching Streamlit Dashboard (http://localhost:8501)...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_path),
        "--server.port=8501",
        "--server.headless=false"
    ])

    # When Streamlit exits, kill ERP process
    print("\n🛑 Shutting down Mock ERP API...")
    erp_process.terminate()
