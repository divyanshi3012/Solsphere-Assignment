
---

### ✅ PART 2: BACKEND API

> 📁 `backend/main.py`

```python
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional
import sqlite3, csv
from fastapi.responses import FileResponse

app = FastAPI()
conn = sqlite3.connect("health.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS machines (
    machine_id TEXT, os TEXT, disk_encryption INTEGER,
    os_update_status TEXT, antivirus_status INTEGER,
    sleep_timeout_ok INTEGER, timestamp TEXT
)
""")
conn.commit()

class SystemData(BaseModel):
    machine_id: str
    os: str
    disk_encryption: bool
    os_update_status: str
    antivirus_status: bool
    sleep_timeout_ok: bool
    timestamp: str

@app.post("/submit")
def submit_data(data: SystemData):
    cursor.execute("DELETE FROM machines WHERE machine_id = ?", (data.machine_id,))
    cursor.execute("INSERT INTO machines VALUES (?, ?, ?, ?, ?, ?, ?)", (
        data.machine_id, data.os, int(data.disk_encryption),
        data.os_update_status, int(data.antivirus_status),
        int(data.sleep_timeout_ok), data.timestamp
    ))
    conn.commit()
    return {"message": "Stored"}

@app.get("/machines")
def list_machines(os: Optional[str] = None, issues: Optional[bool] = False):
    if issues:
        query = """
        SELECT * FROM machines
        WHERE disk_encryption = 0 OR antivirus_status = 0 OR os_update_status != 'True' OR sleep_timeout_ok = 0
        """
        params = ()
        if os:
            query += " AND os = ?"
            params = (os,)
    elif os:
        query = "SELECT * FROM machines WHERE os = ?"
        params = (os,)
    else:
        query = "SELECT * FROM machines"
        params = ()
    rows = cursor.execute(query, params).fetchall()
    return rows

@app.get("/export")
def export_csv(os: Optional[str] = None, issues: Optional[bool] = False):
    rows = list_machines(os=os, issues=issues)
    filename = "report.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["machine_id", "os", "disk_encryption", "os_update_status", "antivirus_status", "sleep_timeout_ok", "timestamp"])
        for row in rows:
            writer.writerow(row)
    return FileResponse(filename)
