import os
import sys
import json
import shutil
import subprocess
import venv

# ------------------------------------------------------------------
#  Paths
# ------------------------------------------------------------------
VENV_DIR = ".venv"
SETTINGS = os.path.join("data", "settings.json")
SETTINGS_TEMPLATE = {
    "volume": 0.8,
    "debug": False,
    "seed": None,
    "window_width": 1280,
    "window_height": 720,
}

# Pip package names vs import names
PIP_PACKAGES = ["PySide6", "perlin-noise"]
IMPORT_NAMES = ["PySide6", "perlin_noise"]


# ------------------------------------------------------------------
#  Helpers
# ------------------------------------------------------------------
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def wait_key():
    if os.name == "nt":
        os.system("pause >nul")
    else:
        input("Press ENTER to continue…")


def run_stream(cmd, *, check=True):
    try:
        subprocess.run(cmd, check=check)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {' '.join(cmd)}")
        raise e


def get_venv_paths():
    if os.name == "nt":
        venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
        venv_pip = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    else:
        venv_python = os.path.join(VENV_DIR, "bin", "python")
        venv_pip = os.path.join(VENV_DIR, "bin", "pip")
    return venv_python, venv_pip


# ------------------------------------------------------------------
#  Core operations
# ------------------------------------------------------------------
def recreate_jsons():
    print("Managing configuration files...")
    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    if os.path.isfile(SETTINGS):
        os.remove(SETTINGS)
        print(f"  Replaced existing '{SETTINGS}'.")
    with open(SETTINGS, "w", encoding="utf-8") as fh:
        json.dump(SETTINGS_TEMPLATE, fh, indent=2)
    print(f"  Created '{SETTINGS}'.")
    print("Configuration files ready.")


def purge_venv():
    print("Cleaning up old virtual environment ('.venv')...")
    if os.path.isdir(VENV_DIR):
        shutil.rmtree(VENV_DIR)
        print("  Removed existing '.venv' directory.")
    else:
        print("  No existing '.venv' directory found. Skipping.")


def create_venv_and_install():
    print("Creating new virtual environment...")
    venv.create(VENV_DIR, with_pip=True)
    print("  .venv directory created.")

    venv_python, venv_pip = get_venv_paths()

    print("\nUpgrading pip to latest version...")
    run_stream([venv_python, "-m", "pip", "install", "--upgrade", "pip"])

    print("\nInstalling required packages (this may take a minute)...")
    run_stream([venv_pip, "install"] + PIP_PACKAGES)
    print("  Packages installed: " + ", ".join(PIP_PACKAGES))


def validate_environment(auto_fix=False):
    print("--- Running Validation ---")
    all_ok = True
    venv_python, venv_pip = get_venv_paths()

    # 1. Virtual environment
    print(f"1. Checking for virtual environment at '{VENV_DIR}'... ", end="")
    if not os.path.exists(venv_python):
        print("FAILED")
        print(f"   Python executable not found at: {os.path.abspath(venv_python)}")
        all_ok = False
        if auto_fix:
            print("   → Attempting to create virtual environment...")
            try:
                create_venv_and_install()
                all_ok = True
                print("   → Virtual environment created successfully.")
            except Exception as e:
                print(f"   → Failed to create venv: {e}")
                return False
    else:
        print("OK")

    # 2. Packages
    print("2. Checking for required packages in .venv...")
    missing = []
    for pkg in IMPORT_NAMES:
        print(f"   - Checking for '{pkg}'... ", end="")
        try:
            subprocess.run(
                [venv_python, "-c", f"import {pkg}"],
                check=True,
                capture_output=True,
                text=True,
            )
            print("OK")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("FAILED")
            missing.append(pkg)
            all_ok = False

    if missing and auto_fix:
        print(f"\n   → Missing packages detected: {', '.join(missing)}")
        print("   → Attempting to install missing packages...")
        try:
            to_install = []
            for m in missing:
                if m == "perlin_noise":
                    to_install.append("perlin-noise")
                elif m == "PySide6":
                    to_install.append("PySide6")
                else:
                    to_install.append(m)
            run_stream([venv_pip, "install"] + to_install)
            still_missing = []
            for pkg in missing:
                try:
                    subprocess.run(
                        [venv_python, "-c", f"import {pkg}"],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                except Exception:
                    still_missing.append(pkg)
            if still_missing:
                print(f"   → Still missing after install: {still_missing}")
                all_ok = False
            else:
                print("   → All missing packages installed successfully.")
                all_ok = True
        except Exception as e:
            print(f"   → Install attempt failed: {e}")
            all_ok = False

    # 3. Configuration files
    print("3. Checking configuration files... ", end="")
    if os.path.isfile(SETTINGS):
        print("OK")
    else:
        print("MISSING")
        all_ok = False
        if auto_fix:
            print("   → Recreating configuration files...")
            recreate_jsons()
            all_ok = True

    print("-" * 40)
    if all_ok:
        print("Validation successful! Environment is ready.")
    else:
        print("Validation failed.")
        if not auto_fix:
            print("Run option 1 (Clean/Purge Install) or option 2 with auto-fix.")
    return all_ok


def clean_purge_install():
    clear_screen()
    print("=" * 79)
    print("    Jules' Text Adventure Game - Clean / Purge Install")
    print("=" * 79)
    print()

    recreate_jsons()
    print()
    purge_venv()
    print()
    create_venv_and_install()

    print("\n--- Installation Report ---")
    print("All steps completed successfully!")
    print(f"Virtual environment : {os.path.abspath(VENV_DIR)}")
    print(f"Packages installed  : {', '.join(PIP_PACKAGES)}")
    print(f"Config created      : {SETTINGS}")
    print("You can now run the game from the main menu.")
    print("-" * 79)


# ------------------------------------------------------------------
#  Menu
# ------------------------------------------------------------------
def show_install_menu():
    while True:
        clear_screen()
        print("=" * 79)
        print("    Jules' Text Adventure Game - Installer Menu")
        print("=" * 79)
        print()
        print("  1) Clean / Purge Install")
        print("     (Wipe .venv + settings, create everything fresh)")
        print()
        print("  2) Check Install / Complete")
        print("     (Validate environment; install anything that is missing)")
        print()
        print("  3) Re-Create Jsons / Inis")
        print("     (Only rewrite configuration files, leave venv alone)")
        print()
        print("  X) Return to Main Menu")
        print()
        print("-" * 79)

        choice = input("Enter your choice: ").strip().upper()

        if choice == "1":
            clean_purge_install()
            print("\nPress any key to return to the main menu...")
            wait_key()
            break                       # exit installer → back to batch
        elif choice == "2":
            clear_screen()
            print("=" * 79)
            print("    Check Install / Complete")
            print("=" * 79)
            print()
            validate_environment(auto_fix=True)
            print("\nPress any key to return to the main menu...")
            wait_key()
            break
        elif choice == "3":
            clear_screen()
            print("=" * 79)
            print("    Re-Create Configuration Files")
            print("=" * 79)
            print()
            recreate_jsons()
            print("\nPress any key to return to the main menu...")
            wait_key()
            break
        elif choice == "X":
            break
        else:
            print("Invalid choice.")
            wait_key()


if __name__ == "__main__":
    show_install_menu()
