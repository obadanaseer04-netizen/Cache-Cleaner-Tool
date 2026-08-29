# 🧹 Windows Cache Cleaner

A modern, fast, and safe Windows system utility written in Python using Tkinter. It automates the process of cleaning temporary cache folders (`%TEMP%`, `TEMP`, and `Prefetch`) with real-time statistics, progress indicators, and an interactive dark-themed GUI.

---

## ✨ Features
* **One-Click Cleaning:** Automatically targets `TEMP`, `%TEMP%`, and `Prefetch` directories.
* **Safe Deletion:** Skips locked/in-use system files gracefully without crashing.
* **Administrator Privileges Support:** Automatically requests UAC elevation to clean protected paths like `Prefetch`.
* **Dark Theme UI:** Built with standard Tkinter for a sleek and clean look.
* **Non-Blocking UI:** Runs cleaning operations in a background thread to keep the application responsive.

---

## 🛠️ Requirements & Dependencies

This tool is built entirely using **Python Standard Libraries**. 
No external packages are required to run the script!

* **Python 3.x** installed on Windows.
* **Standard Built-in Libraries:**
  * `tkinter` (GUI Framework)
  * `threading` & `queue` (Multithreading support)
  * `ctypes` (Windows UAC privilege elevation)
  * `os`, `sys`, `shutil`, `pathlib` (File system operations)

---

## 🚀 How to Run

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/cache-cleaner.git](https://github.com/YOUR_USERNAME/cache-cleaner.git)
   cd cache-cleaner

   ## 🛠️ Required Libraries & Dependencies

This project uses **Python Standard Libraries** only. No external `pip` installations are required to run the source code:

* `tkinter` - For the graphical user interface (GUI)
* `threading` & `queue` - For background execution without freezing the UI
* `ctypes` - For requesting Windows UAC Administrator privileges
* `os`, `sys`, `shutil`, `pathlib` - For file system management and path resolution

---

## 🚀 Usage Commands

### Running the Python Script:
```bash
python cache_cleaner.py
