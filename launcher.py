import os
import sys
import subprocess

VENV_DIR = ".venv"
GAME_SCRIPT = os.path.join("scripts", "game.py")

if sys.platform == "win32":
    VENV_PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
else:
    VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")


def main():
    if not os.path.exists(VENV_PYTHON):
        print("\n[CRITICAL ERROR] Virtual environment not found.")
        print(f"Looked for: {os.path.abspath(VENV_PYTHON)}")
        print("Please run the Installer (option 3) and choose Clean/Purge or Check Install.")
        if sys.platform == "win32":
            os.system("pause")
        sys.exit(1)

    if not os.path.exists(GAME_SCRIPT):
        print(f"\n[CRITICAL ERROR] Game script not found at '{GAME_SCRIPT}'.")
        if sys.platform == "win32":
            os.system("pause")
        sys.exit(1)

    try:
        subprocess.run([VENV_PYTHON, GAME_SCRIPT], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nAn error occurred while running the game: {e}")
        if sys.platform == "win32":
            os.system("pause")
    except FileNotFoundError:
        print(f"\n[CRITICAL ERROR] Could not execute Python from the virtual environment.")
        print(f"Path may be incorrect: {os.path.abspath(VENV_PYTHON)}")
        if sys.platform == "win32":
            os.system("pause")
        sys.exit(1)


if __name__ == "__main__":
    main()
