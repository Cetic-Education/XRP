import os
import subprocess
import sys
import winreg
import time

def run_command(command, description):
    """
    Executes a shell command, prints its output in real-time, and checks for errors.
    """
    print(f"\n--- {description} ---")
    try:
        # Using subprocess.Popen to capture output in real-time
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        # Wait for the process to complete and get the return code
        return_code = process.wait()

        if return_code != 0:
            print(f"\n[ERROR] Command failed with exit code {return_code}.")
            return False
        
        print(f"[SUCCESS] {description} completed successfully.")
        return True

    except FileNotFoundError:
        print(f"\n[ERROR] Command not found. Please ensure the command is correct and in your system's PATH.")
        return False
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")
        return False
def check_internet():
    """
    嘗試 Ping 來確認是否有外網連接。
    """
    print("\n--- Checking Internet Connection ---")
    try:
        # -n 1: 嘗試一次, -w 3000: 等待 3 秒超時
        subprocess.check_call("ping -n 1 -w 3000 1.1.1.1", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[INFO] Internet connection is active.")
        return True
    except subprocess.CalledProcessError:
        print("[WARNING] No internet connection detected.")
        return False

def connect_wifi(ssid, password):
    """
    生成 Wi-Fi XML 設定檔並嘗試連接。
    僅支援最常見的 WPA2-Personal (AES) 加密方式。
    """
    print(f"\n--- Attempting to connect to Wi-Fi: {ssid} ---")
    
    # 定義 Wi-Fi Profile 的 XML 模板 (WPA2-PSK)
    # 注意：這裡假設 keyType 是 passPhrase (密碼)，encryption 是 AES
    profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""

    # 1. 將 XML 寫入暫存檔案
    xml_filename = "wifi_temp_config.xml"
    try:
        with open(xml_filename, "w", encoding="utf-8") as f:
            f.write(profile_xml)
        
        # 2. 加入 Profile 到系統
        # netsh wlan add profile filename="wifi_temp_config.xml"
        add_cmd = f'netsh wlan add profile filename="{xml_filename}"'
        if not run_command(add_cmd, "Adding Wi-Fi Profile"):
            return False

        # 3. 執行連線
        # netsh wlan connect name="SSID"
        connect_cmd = f'netsh wlan connect name="{ssid}"'
        run_command(connect_cmd, "Connecting to Wi-Fi")

        # 4. 等待幾秒讓 DHCP 分配 IP
        print("[INFO] Waiting for connection to establish...")
        time.sleep(10) # 等待 10 秒

        # 5. 清理 XML 檔案
        if os.path.exists(xml_filename):
            os.remove(xml_filename)

        # 6. 再次檢查網絡
        if check_internet():
            print(f"[SUCCESS] Successfully connected to {ssid}!")
            return True
        else:
            print(f"[ERROR] Connected to Wi-Fi but still no internet access.")
            return False

    except Exception as e:
        print(f"[ERROR] Failed to set up Wi-Fi: {e}")
        return False

def execute_bat(bat_file_path):
    """
    Executes a .bat file located at the given path.
    """
    if not os.path.isfile(bat_file_path):
        print(f"[ERROR] The specified .bat file does not exist: {bat_file_path}")
        return False
    
    return run_command(f'"{bat_file_path}"', f"Executing batch file: {os.path.basename(bat_file_path)}")

def get_startup_folder():
    """
    Retrieves the path to the current user's Startup folder from the registry.
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
        startup_path, _ = winreg.QueryValueEx(key, "Startup")
        winreg.CloseKey(key)
        return os.path.expandvars(startup_path)
    except Exception as e:
        print(f"[ERROR] Could not find startup folder: {e}")
        return None

def create_startup_script(base_path, startup_folder):
    """
    Creates the .bat script in the startup folder to run the main Python app.
    """
    print("\n--- Creating startup script ---")
    venv_python_path = os.path.join(base_path, ".venv", "Scripts", "pythonw.exe")
    main_script_path = os.path.join(base_path, "demo.py") # Assuming main.py is in the base path
    log_file_path = os.path.join(base_path, "logs", "runtime.log")
    
    # Ensure log directory exists
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    # Content of the startup .bat file, adapted from your template
    script_content = f'''@echo off
REM This script runs the main application in the background on startup.

SET "PYTHON_EXE_WINDOWLESS={venv_python_path}"
SET "PYTHON_SCRIPT={main_script_path}"
SET "WORKING_DIRECTORY={base_path}"
SET "LOG_FILE={log_file_path}"

REM Change to the working directory
cd /d %WORKING_DIRECTORY%

REM Execute the python script in the background (no window) and log output/errors.
START "PythonAppBackgroundTask" /B %PYTHON_EXE_WINDOWLESS% %PYTHON_SCRIPT% >> %LOG_FILE% 2>&1
'''

    startup_script_path = os.path.join(startup_folder, "start.bat")
    try:
        with open(startup_script_path, "w") as f:
            f.write(script_content)
        print(f"[SUCCESS] Startup script created at: {startup_script_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create startup script: {e}")
        return False

def check_winget():
    print("\n--- Checking for Winget ---")
    try:
        # Run winget --version to check existence. 
        # Using specific subprocess call to suppress output if we just want to check boolean status
        subprocess.check_call("winget --version", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[INFO] Winget is already installed.")
        return True
    except subprocess.CalledProcessError:
        print("[WARNING] Winget not found.")
        return False


def install_winget():
    print("\n--- Installing Winget (App Installer) ---")
    # PowerShell command to fetch latest release from GitHub API and install it
    ps_command = (
        "$progressPreference = 'SilentlyContinue'; "
        "Write-Host 'Fetching latest Winget version...'; "
        "try { "
        "$latest = Invoke-RestMethod -Uri 'https://api.github.com/repos/microsoft/winget-cli/releases/latest'; "
        "$url = $latest.assets | Where-Object { $_.name -like '*.msixbundle' } | Select-Object -ExpandProperty browser_download_url; "
        "$tempPath = $env:TEMP + '\\winget.msixbundle'; "
        "Write-Host 'Downloading from:' $url; "
        "Invoke-WebRequest -Uri $url -OutFile $tempPath; "
        "Write-Host 'Installing package...'; "
        "Add-AppxPackage -Path $tempPath; "
        "Remove-Item $tempPath; "
        "Write-Host 'Winget installation completed.'; "
        "} catch { "
        "Write-Error $_.Exception.Message; exit 1 "
        "}"
    )
    
    # Run the PowerShell command
    cmd = f'powershell -Command "{ps_command}"'
    if run_command(cmd, "Installing Winget via PowerShell"):
        print("[INFO] Refreshing environment variables...")
        # A workaround to make sure new path is picked up is tricky in the same process,
        # but usually AppxPackage works immediately for new shells.
        return True
    return False
    
if __name__ == "__main__":
    print("--- Installation and Setup Script ---")
    if input("This script will install software and configure your system. Continue? (y/n): ").lower() != 'y':
        print("Aborted by user.")
        sys.exit()
        
    if not check_internet():
        print("\n[!] Internet is required for installation (Winget/RustDesk).")
        print("Would you like to configure Wi-Fi now?")
        choice = input("Enter 'y' to setup Wi-Fi, or any other key to retry/skip: ").lower()
        
        if choice == 'y':
            target_ssid = "ceticfoundation.org"
            target_pw = "intelcrossxrp"
            
            if connect_wifi(target_ssid, target_pw):
                print("\n[INFO] Internet connected. Proceeding with installation...")
            else:
                print("\n[ERROR] Could not connect to internet. Winget installation may fail.")
                if input("Continue anyway? (y/n): ").lower() != 'y':
                    sys.exit()
        else:
            print("[WARNING] Proceeding without verified internet connection.")
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    if not check_winget():
        if install_winget():
            print("[INFO] Winget installed. Note: If the next step fails, please restart this script.")
            time.sleep(2) # Give system a moment
        else:
            print("[ERROR] Failed to install Winget automatically.")
            
    # Step 1: Install RustDesk using winget
    if not run_command("winget install --id RustDesk.RustDesk -e --accept-package-agreements --accept-source-agreements", "Installing RustDesk"):
        print("[WARNING] RustDesk installation failed. It might be already installed. Continuing setup...")

    # Step 2: Create venv and install requirements
    venv_bat_path = os.path.join(base_path, 'oneclick_install_with_venv.bat')
    if not execute_bat(venv_bat_path):
        print("Virtual environment setup failed. Please check 'oneclick_install_with_venv.bat'. Exiting.")
        sys.exit(1)

    # Step 3: Create startup script
    startup_folder = get_startup_folder()
    if startup_folder and create_startup_script(base_path, startup_folder):
        print("\nSetup complete! The application will start automatically the next time you log in.")
    else:
        print("\nCould not create the startup script. You will need to run the application manually.")
        sys.exit(1)
