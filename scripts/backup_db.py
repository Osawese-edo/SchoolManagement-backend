import os
import subprocess
import sys
from datetime import datetime, timezone

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backups")
DB_URL = os.getenv("DATABASE_URL", "")


def run_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"destined_backup_{timestamp}.sql"
    filepath = os.path.join(BACKUP_DIR, filename)

    if not DB_URL:
        print("DATABASE_URL not set")
        sys.exit(1)

    parts = DB_URL.replace("postgresql://", "").split("@")
    user_pass, host_db = parts[0], parts[1]
    user, pw = user_pass.split(":")
    host_port, dbname = host_db.split("/")
    host, port = host_port.split(":") if ":" in host_port else (host_port, "5432")

    os.environ["PGPASSWORD"] = pw
    cmd = [
        "pg_dump",
        "-h", host,
        "-p", port,
        "-U", user,
        "-d", dbname,
        "-F", "c",
        "-f", filepath,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Backup saved: {filepath}")
    else:
        print(f"Backup failed: {result.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    run_backup()
