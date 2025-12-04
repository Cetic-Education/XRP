import os
import subprocess
import sys
import winreg

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

if __name__ == "__main__":
    print("--- Installation and Setup Script ---")
    if input("This script will install software and configure your system. Continue? (y/n): ").lower() != 'y':
        print("Aborted by user.")
        sys.exit()

    base_path = os.path.dirname(os.path.abspath(__file__))

    # Step 1: Install RustDesk using winget
    if not run_command("winget install --id RustDesk.RustDesk -e --accept-package-agreements --accept-source-agreements", "Installing RustDesk"):
        print("RustDesk installation failed. Please try installing it manually. Exiting.")
        sys.exit(1)

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
