# 🧹 Windows Cache Cleaner

A modern, fast, and safe Windows system utility written in Python using Tkinter. It automates the process of moving temporary cache files to the **Recycle Bin**, trimming **Memory Cache**, flushing **DNS**, and running system cleanup tools with real-time statistics and an interactive dark-themed GUI.

---

## ✨ Features

* **Safe File Cleaning (To Recycle Bin):** Targets `TEMP`, `%TEMP%`, and `Prefetch` directories by safely moving files and folders to the Windows Recycle Bin instead of deleting them permanently.
* **Memory Cache Optimization:** Safely trims active process working sets to free up standby RAM without risking system stability.
* **Dedicated Empty Recycle Bin:** Located in the bottom action bar with a prominent red highlight and a confirmation dialog to prevent accidental permanent data loss.
* **DNS Cache Flushing:** Flushes the Windows DNS resolver cache directly within the app to restore network connectivity.
* **Disk Cleanup Launcher:** Quick one-click launch for the built-in Windows Disk Cleanup utility (`cleanmgr.exe`).
* **Disabled NVIDIA DX Cache:** Button remains visible but disabled to protect graphics shader cache from unintended modification.
* **Activity Log & Real-Time Stats:** Live queue-based logging and statistical dashboard tracking moved files, folders, skipped items, and processed space.
* **Non-Blocking UI:** Runs all cleaning and system operations in background threads to keep the interface smooth and responsive.
* **Admin Privileges Support:** Automatically requests UAC elevation for full access to protected system directories like `Prefetch`.

---

## 🛠️ Requirements & Dependencies

This tool is built entirely using **Python Standard Libraries** and Win32 APIs via `ctypes`. No third-party package installations are required to run the script!

* **Windows OS** (Windows 10/11 recommended).
* **Python 3.x** installed.
* **Standard Built-in Libraries:**
  * `tkinter` (GUI Framework)
  * `ctypes` (Win32 API integration & UAC elevation)
  * `threading` & `queue` (Multithreading support)
  * `os`, `sys`, `pathlib`, `subprocess` (System & File operations)

---

## 🚀 How to Run

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/obadanaseer04-netizen/cache-cleaner.git](https://github.com/obadanaseer04-netizen/cache-cleaner.git)
   cd cache-cleaner

---

## 🚀 How to Run

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/obadanaseer04-netizen/cache-cleaner.git](https://github.com/obadanaseer04-netizen/cache-cleaner.git)
   cd cache-cleaner

   ---

## 📦 Building Executable (.exe)

If you want to build a standalone Windows executable (`.exe`):

1. **Install PyInstaller:**
   ```bash
   pip install pyinstaller

2. **Build the EXE file:**
    ```bash
   pyinstaller --noconsole --onefile --uac-admin cache_cleaner.py
The compiled .exe will be located inside the dist/ directory.
   
   
## 🛡️ Safety & Security
Undo Support: Files moved via CLEAN go directly to the Windows Recycle Bin, allowing full recovery if needed.

No Auto-Run Events: Resizing, maximizing, or restoring the window will never trigger auto-cleaning routines.

Locked File Handling: In-use or system-protected files are gracefully skipped and logged without crashing the app.
