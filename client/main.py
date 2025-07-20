import platform, subprocess, time, uuid, os, requests, schedule, json

with open("config.json") as f:
    config = json.load(f)

API_ENDPOINT = config["API_ENDPOINT"]
MACHINE_ID = str(uuid.getnode())
previous_state = {}

def get_os_info():
    return platform.system(), platform.release()

def check_disk_encryption():
    os_type, _ = get_os_info()
    try:
        if os_type == "Windows":
            result = subprocess.check_output(['manage-bde', '-status', 'C:']).decode()
            return "Protection On" in result
        elif os_type == "Darwin":
            result = subprocess.check_output(['fdesetup', 'status']).decode()
            return "FileVault is On" in result
        elif os_type == "Linux":
            return os.path.exists('/etc/crypttab')
    except: return None

def check_os_update():
    os_type, _ = get_os_info()
    try:
        if os_type == "Windows": return "unknown"
        elif os_type == "Darwin":
            output = subprocess.check_output(['softwareupdate', '-l']).decode()
            return "No new software available" in output
        elif os_type == "Linux":
            result = subprocess.check_output(['apt', 'list', '--upgradable']).decode()
            return len(result.strip().split('\n')) <= 1
    except: return None

def check_antivirus():
    os_type, _ = get_os_info()
    try:
        if os_type == "Windows": return True
        elif os_type == "Darwin": return os.path.exists('/Applications/Norton Security.app')
        elif os_type == "Linux":
            result = subprocess.run(['systemctl', 'is-active', 'clamav-daemon'], capture_output=True, text=True)
            return 'active' in result.stdout
    except: return None

def check_sleep_timeout():
    os_type, _ = get_os_info()
    try:
        if os_type == "Darwin":
            result = subprocess.check_output(['pmset', '-g']).decode()
            for line in result.splitlines():
                if 'sleep' in line:
                    mins = int(line.strip().split()[-1])
                    return mins <= 10
        elif os_type == "Linux":
            result = subprocess.check_output(['gsettings', 'get', 'org.gnome.settings-daemon.plugins.power', 'sleep-inactive-ac-timeout']).decode()
            return int(result.strip()) <= 600
        elif os_type == "Windows": return True  # Assume OK
    except: return None

def collect_data():
    return {
        "machine_id": MACHINE_ID,
        "os": platform.system(),
        "disk_encryption": check_disk_encryption(),
        "os_update_status": str(check_os_update()),
        "antivirus_status": check_antivirus(),
        "sleep_timeout_ok": check_sleep_timeout(),
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    }

def send_if_changed():
    global previous_state
    current_data = collect_data()
    if current_data != previous_state:
        try:
            res = requests.post(API_ENDPOINT, json=current_data)
            if res.status_code == 200:
                print("✅ Data sent.")
                previous_state = current_data
        except Exception as e:
            print("❌ Failed to send:", e)
    else:
        print("⏸ No change.")

schedule.every(15).minutes.do(send_if_changed)

if __name__ == "__main__":
    send_if_changed()
    while True:
        schedule.run_pending()
        time.sleep(60)
