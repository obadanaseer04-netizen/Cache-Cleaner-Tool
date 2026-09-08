import os
import sys
import shutil
import pathlib
import threading
import queue
import ctypes
from ctypes import wintypes
import subprocess
import time
import tkinter as tk
from tkinter import ttk, messagebox

# Win32 Structures for Moving to Recycle Bin safely via Shell API
class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_ushort),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", wintypes.LPVOID),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]

FO_DELETE = 0x0003
FOF_ALLOWUNDO = 0x0040
FOF_NOCONFIRMATION = 0x0010
FOF_SILENT = 0x0004
FOF_NOERRORUI = 0x0400

SHERB_NOCONFIRMATION = 0x00000001
SHERB_NOPROGRESSUI = 0x00000002
SHERB_NOSOUND = 0x00000004

def move_to_recycle_bin(path_str):
    """Safely moves a file or folder to the Windows Recycle Bin."""
    try:
        # Path must be double-null terminated for SHFileOperationW
        double_null_path = path_str + "\0\0"
        fileop = SHFILEOPSTRUCTW()
        fileop.hwnd = 0
        fileop.wFunc = FO_DELETE
        fileop.pFrom = double_null_path
        fileop.pTo = None
        fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        
        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
        return result == 0 and not fileop.fAnyOperationsAborted
    except Exception:
        return False

# Hide Console Window on Windows if running via python.exe / executable
def hide_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd != 0:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # 0 = SW_HIDE
    except Exception:
        pass

# Check and request Administrator privileges on Windows
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_as_admin():
    if not is_admin():
        try:
            if getattr(sys, 'frozen', False):
                executable = sys.executable
                args = " ".join(f'"{arg}"' for arg in sys.argv[1:])
            else:
                python_exe = sys.executable
                if python_exe.endswith("python.exe"):
                    pythonw = python_exe[:-10] + "pythonw.exe"
                    if os.path.exists(pythonw):
                        python_exe = pythonw
                executable = python_exe
                args = " ".join(f'"{arg}"' for arg in sys.argv)

            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", executable, args, None, 1
            )
            sys.exit(0)
        except Exception as e:
            print(f"Failed to elevate permissions: {e}")

class CacheCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows Cache Cleaner")
        self.root.geometry("820x680")
        self.root.minsize(700, 480)
        self.root.configure(bg="#1e1e2e")

        # Application state flags
        self.is_cleaning = False
        self.log_queue = queue.Queue()

        # Custom Styling
        self.setup_styles()

        # UI Components Construction
        self.build_ui()

        # Start listening to UI log updates safely from background thread
        self.root.after(100, self.process_log_queue)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('default')

        # Configure Dark Palette Colors
        self.bg_color = "#1e1e2e"
        self.card_color = "#252538"
        self.text_color = "#cdd6f4"
        self.accent_color = "#89b4fa"
        self.accent_hover = "#b4befe"
        self.danger_color = "#f38ba8"
        self.danger_hover = "#f5e0dc"
        self.success_color = "#a6e3a1"
        self.muted_color = "#6c7086"

        # Style Progressbar
        self.style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor="#313244",
            background=self.accent_color,
            thickness=10,
            borderwidth=0
        )

    def build_ui(self):
        # Header Section
        header_frame = tk.Frame(self.root, bg=self.bg_color)
        header_frame.pack(fill="x", padx=15, pady=(10, 2))

        title_label = tk.Label(
            header_frame, text="Windows Cache Cleaner",
            font=("Segoe UI", 16, "bold"), fg=self.text_color, bg=self.bg_color
        )
        title_label.pack(anchor="w")

        subtitle_label = tk.Label(
            header_frame, text="Clean temporary files, Memory Cache, DNS Cache, and Windows Disk Cleanup safely",
            font=("Segoe UI", 9), fg=self.muted_color, bg=self.bg_color
        )
        subtitle_label.pack(anchor="w")

        # Admin status badge
        admin_text = "🛡️ Admin Privileges: Active" if is_admin() else "⚠️ Standard User (Limited Prefetch & Memory access)"
        admin_color = self.success_color if is_admin() else "#f9e2af"
        admin_label = tk.Label(
            header_frame, text=admin_text,
            font=("Segoe UI", 8, "bold"), fg=admin_color, bg=self.bg_color
        )
        admin_label.pack(anchor="w", pady=(2, 0))

        # Action Section (Clean Buttons Grid - 5 columns)
        action_frame = tk.Frame(self.root, bg=self.bg_color)
        action_frame.pack(fill="x", padx=15, pady=6)

        for i in range(5):
            action_frame.columnconfigure(i, weight=1)

        self.clean_btn = tk.Button(
            action_frame, text="CLEAN\n(Temp & Prefetch)", font=("Segoe UI", 8, "bold"),
            bg=self.accent_color, fg="#11111b", activebackground=self.accent_hover,
            activeforeground="#11111b", bd=0, relief="flat", cursor="hand2",
            command=self.start_cleanup_thread, pady=6
        )
        self.clean_btn.grid(row=0, column=0, sticky="nsew", padx=(0, 2))

        self.memory_btn = tk.Button(
            action_frame, text="MEMORY CACHE\n(Trim Working Set)", font=("Segoe UI", 8, "bold"),
            bg=self.accent_color, fg="#11111b", activebackground=self.accent_hover,
            activeforeground="#11111b", bd=0, relief="flat", cursor="hand2",
            command=self.start_memory_cleanup_thread, pady=6
        )
        self.memory_btn.grid(row=0, column=1, sticky="nsew", padx=2)

        # NVIDIA DX CACHE Button - Visual Only (Disabled & No Action)
        self.nvidia_btn = tk.Button(
            action_frame, text="NVIDIA DX CACHE\n(Disabled)", font=("Segoe UI", 8, "bold"),
            bg="#45475a", fg=self.muted_color, activebackground="#45475a",
            activeforeground=self.muted_color, bd=0, relief="flat", cursor="arrow",
            state="disabled", command=self.disabled_action, pady=6
        )
        self.nvidia_btn.grid(row=0, column=2, sticky="nsew", padx=2)

        self.dns_btn = tk.Button(
            action_frame, text="DNS CACHE\n(Flush DNS)", font=("Segoe UI", 8, "bold"),
            bg=self.accent_color, fg="#11111b", activebackground=self.accent_hover,
            activeforeground="#11111b", bd=0, relief="flat", cursor="hand2",
            command=self.start_dns_cleanup_thread, pady=6
        )
        self.dns_btn.grid(row=0, column=3, sticky="nsew", padx=2)

        self.disk_clean_btn = tk.Button(
            action_frame, text="DISK CLEANUP\n(Windows Tool)", font=("Segoe UI", 8, "bold"),
            bg=self.accent_color, fg="#11111b", activebackground=self.accent_hover,
            activeforeground="#11111b", bd=0, relief="flat", cursor="hand2",
            command=self.open_disk_cleanup, pady=6
        )
        self.disk_clean_btn.grid(row=0, column=4, sticky="nsew", padx=(2, 0))

        # Progress Section
        progress_frame = tk.Frame(self.root, bg=self.bg_color)
        progress_frame.pack(fill="x", padx=15, pady=4)

        self.status_label = tk.Label(
            progress_frame, text="Ready", font=("Segoe UI", 9),
            fg=self.text_color, bg=self.bg_color
        )
        self.status_label.pack(anchor="w", pady=(0, 3))

        self.progress_bar = ttk.Progressbar(
            progress_frame, style="Custom.Horizontal.TProgressbar",
            orient="horizontal", mode="determinate"
        )
        self.progress_bar.pack(fill="x")

        # Statistics Dashboard
        stats_frame = tk.Frame(self.root, bg=self.card_color, bd=1, relief="solid")
        stats_frame.pack(fill="x", padx=15, pady=6)

        for i in range(4):
            stats_frame.columnconfigure(i, weight=1)

        self.lbl_files = self.create_stat_box(stats_frame, "Files Moved", "0", 0)
        self.lbl_folders = self.create_stat_box(stats_frame, "Folders Moved", "0", 1)
        self.lbl_skipped = self.create_stat_box(stats_frame, "Skipped", "0", 2)
        self.lbl_space = self.create_stat_box(stats_frame, "Space Processed", "0 B", 3)

        # Bottom Bar / Footer Buttons
        footer_frame = tk.Frame(self.root, bg=self.bg_color)
        footer_frame.pack(side="bottom", fill="x", padx=15, pady=(4, 10))

        self.clear_log_btn = tk.Button(
            footer_frame, text="CLEAR LOG", font=("Segoe UI", 8, "bold"),
            bg="#313244", fg=self.text_color, activebackground="#45475a",
            activeforeground=self.text_color, bd=0, relief="flat", cursor="hand2",
            command=self.clear_log, padx=12, pady=4
        )
        self.clear_log_btn.pack(side="left")

        self.empty_recycle_btn = tk.Button(
            footer_frame, text="EMPTY RECYCLE BIN", font=("Segoe UI", 8, "bold"),
            bg=self.danger_color, fg="#11111b", activebackground=self.danger_hover,
            activeforeground="#11111b", bd=0, relief="flat", cursor="hand2",
            command=self.start_empty_recycle_bin_thread, padx=12, pady=4
        )
        self.empty_recycle_btn.pack(side="left", padx=8)

        self.exit_btn = tk.Button(
            footer_frame, text="EXIT", font=("Segoe UI", 8, "bold"),
            bg="#313244", fg=self.danger_color, activebackground="#45475a",
            activeforeground=self.danger_color, bd=0, relief="flat", cursor="hand2",
            command=self.on_exit, padx=12, pady=4
        )
        self.exit_btn.pack(side="right")

        # Activity Log Section
        log_frame = tk.Frame(self.root, bg=self.bg_color)
        log_frame.pack(side="top", fill="both", expand=True, padx=15, pady=(0, 4))

        log_title = tk.Label(
            log_frame, text="Activity Log", font=("Segoe UI", 9, "bold"),
            fg=self.text_color, bg=self.bg_color
        )
        log_title.pack(anchor="w", pady=(0, 3))

        self.log_text = tk.Text(
            log_frame, bg="#11111b", fg=self.text_color, font=("Consolas", 8),
            bd=0, relief="flat", state="disabled", wrap="word", height=6
        )
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview, bg=self.card_color)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

    def create_stat_box(self, parent, title, initial_val, col):
        frame = tk.Frame(parent, bg=self.card_color, pady=6)
        frame.grid(row=0, column=col, sticky="nsew")

        val_lbl = tk.Label(
            frame, text=initial_val, font=("Segoe UI", 11, "bold"),
            fg=self.accent_color, bg=self.card_color
        )
        val_lbl.pack()

        title_lbl = tk.Label(
            frame, text=title, font=("Segoe UI", 8),
            fg=self.muted_color, bg=self.card_color
        )
        title_lbl.pack()

        return val_lbl

    def set_buttons_state(self, state):
        btn_state = "disabled" if state == "disabled" else "normal"
        bg_color = "#45475a" if state == "disabled" else self.accent_color
        danger_bg = "#45475a" if state == "disabled" else self.danger_color

        self.clean_btn.config(state=btn_state, bg=bg_color)
        self.memory_btn.config(state=btn_state, bg=bg_color)
        self.dns_btn.config(state=btn_state, bg=bg_color)
        self.disk_clean_btn.config(state=btn_state, bg=bg_color)
        self.empty_recycle_btn.config(state=btn_state, bg=danger_bg)
        
        # NVIDIA Button remains permanently disabled visually
        self.nvidia_btn.config(state="disabled", bg="#45475a")

    def disabled_action(self, event=None):
        pass

    def log(self, message):
        self.log_queue.put(message)

    def process_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(100, self.process_log_queue)

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def format_size(self, size_bytes):
        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = 0
        p = 1024
        while size_bytes >= p and i < len(size_name) - 1:
            size_bytes /= p
            i += 1
        return f"{size_bytes:.2f} {size_name[i]}"

    def get_target_directories(self):
        target_dirs = []
        
        # 1. System TEMP (%WINDIR%\Temp)
        system_temp = os.environ.get("SYSTEMROOT", "C:\\Windows") + "\\Temp"
        target_dirs.append(("TEMP", pathlib.Path(system_temp)))

        # 2. User TEMP (%USERPROFILE%\AppData\Local\Temp)
        user_temp = os.environ.get("TEMP") or os.environ.get("TMP")
        if user_temp:
            target_dirs.append(("%TEMP%", pathlib.Path(user_temp)))

        # 3. Windows Prefetch (%WINDIR%\Prefetch)
        prefetch = os.environ.get("SYSTEMROOT", "C:\\Windows") + "\\Prefetch"
        target_dirs.append(("Prefetch", pathlib.Path(prefetch)))

        return target_dirs

    def start_cleanup_thread(self, event=None):
        if self.is_cleaning:
            return
        
        self.is_cleaning = True
        self.set_buttons_state("disabled")
        self.progress_bar["value"] = 0
        
        threading.Thread(target=self.run_cleanup_process, daemon=True).start()

    def run_cleanup_process(self):
        self.log("[+] Starting cleanup (Moving files to Recycle Bin)...")
        
        total_files_moved = 0
        total_folders_moved = 0
        total_skipped = 0
        total_bytes_processed = 0

        target_dirs = self.get_target_directories()
        step_increment = 100 / max(len(target_dirs), 1)

        for idx, (label, dir_path) in enumerate(target_dirs):
            self.status_label.config(text=f"Cleaning {label}...")
            self.log(f"[+] Processing directory {label}: {dir_path}")

            if not dir_path.exists() or not dir_path.is_dir():
                self.log(f"[!] Path does not exist or is inaccessible: {dir_path}")
                self.progress_bar["value"] = (idx + 1) * step_increment
                continue

            files_mov, flds_mov, skipped, bytes_proc = self.clean_single_directory(dir_path)
            
            total_files_moved += files_mov
            total_folders_moved += flds_mov
            total_skipped += skipped
            total_bytes_processed += bytes_proc

            self.progress_bar["value"] = (idx + 1) * step_increment
            
            self.lbl_files.config(text=str(total_files_moved))
            self.lbl_folders.config(text=str(total_folders_moved))
            self.lbl_skipped.config(text=str(total_skipped))
            self.lbl_space.config(text=self.format_size(total_bytes_processed))

        self.status_label.config(text="Cleaning completed (Moved to Recycle Bin)")
        self.log("[✓] Cleanup process finished! All items moved to Recycle Bin.")
        self.log(f"    Summary: {total_files_moved} Files Moved, {total_folders_moved} Folders Moved, {total_skipped} Skipped, {self.format_size(total_bytes_processed)} Processed.")

        self.set_buttons_state("normal")
        self.is_cleaning = False

        messagebox.showinfo(
            "Cleanup Completed!",
            f"Temporary files have been moved to Recycle Bin.\n\n"
            f"• Files Moved: {total_files_moved}\n"
            f"• Folders Moved: {total_folders_moved}\n"
            f"• Space Processed: {self.format_size(total_bytes_processed)}\n"
            f"• Skipped (In Use): {total_skipped}"
        )

    def clean_single_directory(self, folder_path):
        files_moved = 0
        folders_moved = 0
        skipped = 0
        bytes_processed = 0

        try:
            entries = list(folder_path.iterdir())
        except Exception as e:
            self.log(f"[!] Error accessing folder {folder_path}: {e}")
            return files_moved, folders_moved, 1, bytes_processed

        for entry in entries:
            try:
                path_str = str(entry.resolve())
                
                if entry.is_file() or entry.is_symlink():
                    try:
                        file_size = entry.stat().st_size
                    except Exception:
                        file_size = 0

                    if move_to_recycle_bin(path_str):
                        files_moved += 1
                        bytes_processed += file_size
                        self.log(f"[+] Moved to Recycle Bin: {entry.name}")
                    else:
                        skipped += 1
                        self.log(f"[!] Skipped (In use / Protected): {entry.name}")

                elif entry.is_dir():
                    if move_to_recycle_bin(path_str):
                        folders_moved += 1
                        self.log(f"[+] Moved directory to Recycle Bin: {entry.name}")
                    else:
                        skipped += 1
                        self.log(f"[!] Skipped folder (In use / Protected): {entry.name}")

            except Exception as e:
                skipped += 1
                self.log(f"[!] Error processing {entry.name}: {e}")

        return files_moved, folders_moved, skipped, bytes_processed

    def start_memory_cleanup_thread(self, event=None):
        if self.is_cleaning:
            return

        self.is_cleaning = True
        self.set_buttons_state("disabled")
        self.progress_bar["value"] = 0

        threading.Thread(target=self.run_memory_cleanup_process, daemon=True).start()

    def run_memory_cleanup_process(self):
        self.log("[+] Starting Memory Cache Cleanup (Trimming Process Working Sets)...")
        self.status_label.config(text="Cleaning Memory Cache...")
        self.progress_bar["value"] = 20

        success_count = 0
        fail_count = 0

        try:
            # PROCESS_SET_QUOTA = 0x0100, PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_ALL_ACCESS = 0x1F0FFF
            PROCESS_SET_QUOTA = 0x0100

            # Get EnumProcesses
            psapi = ctypes.windll.psapi
            kernel32 = ctypes.windll.kernel32

            arr = (wintypes.DWORD * 4096)()
            cbNeeded = wintypes.DWORD()

            if psapi.EnumProcesses(ctypes.byref(arr), ctypes.sizeof(arr), ctypes.byref(cbNeeded)):
                num_processes = int(cbNeeded.value / ctypes.sizeof(wintypes.DWORD))
                self.log(f"[+] Found {num_processes} active processes to analyze.")

                for i in range(num_processes):
                    pid = arr[i]
                    if pid == 0:
                        continue
                    
                    # Open Process
                    hProcess = kernel32.OpenProcess(PROCESS_SET_QUOTA, False, pid)
                    if hProcess:
                        # SetProcessWorkingSetSize(hProcess, -1, -1) flushes standby memory pages
                        res = kernel32.SetProcessWorkingSetSize(hProcess, ctypes.c_size_t(-1), ctypes.c_size_t(-1))
                        if res:
                            success_count += 1
                        else:
                            fail_count += 1
                        kernel32.CloseHandle(hProcess)
                    else:
                        fail_count += 1

                    if i % 10 == 0:
                        self.progress_bar["value"] = 20 + int((i / max(num_processes, 1)) * 70)

            self.progress_bar["value"] = 100
            self.log("[✓] Memory Cache cleanup completed successfully.")
            self.log(f"    Summary: {success_count} Processes Trimmed, {fail_count} Skipped/Protected.")
            self.status_label.config(text="Memory Cache cleaned successfully")

            messagebox.showinfo(
                "Memory Cache Cleaned",
                f"Memory Cache optimization complete.\n\n"
                f"• Process Working Sets Trimmed: {success_count}\n"
                f"• Skipped / System Protected: {fail_count}"
            )

        except Exception as e:
            self.progress_bar["value"] = 100
            self.log(f"[!] Error cleaning Memory Cache: {e}")
            self.status_label.config(text="Error cleaning Memory Cache")
            messagebox.showerror("Memory Cache Error", f"An error occurred while cleaning Memory Cache:\n{e}")

        self.set_buttons_state("normal")
        self.is_cleaning = False

    def start_empty_recycle_bin_thread(self, event=None):
        if self.is_cleaning:
            return

        # Confirmation Dialog
        if not messagebox.askyesno("Confirmation Required", "Are you sure you want to permanently empty the entire Recycle Bin?"):
            self.log("[!] Operation canceled by user.")
            return

        self.is_cleaning = True
        self.set_buttons_state("disabled")
        self.progress_bar["value"] = 0

        threading.Thread(target=self.run_empty_recycle_bin_process, daemon=True).start()

    def run_empty_recycle_bin_process(self):
        self.log("[+] Emptying Recycle Bin permanently...")
        self.status_label.config(text="Emptying Recycle Bin...")
        self.progress_bar["value"] = 50

        try:
            flags = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
            result = ctypes.windll.shell32.SHEmptyRecycleBinW(0, None, flags)
            
            self.progress_bar["value"] = 100

            if result == 0:
                self.log("[✓] Recycle Bin emptied successfully.")
                self.status_label.config(text="Recycle Bin emptied successfully")
                messagebox.showinfo("Recycle Bin", "Recycle Bin has been emptied successfully.")
            else:
                self.log(f"[!] Failed to empty Recycle Bin or it is already empty. Result Code: {result}")
                self.status_label.config(text="Recycle Bin empty or action completed")
                messagebox.showinfo("Recycle Bin", "Recycle Bin is already empty or operation completed.")

        except Exception as e:
            self.progress_bar["value"] = 100
            self.log(f"[!] Exception occurred while emptying Recycle Bin: {e}")
            self.status_label.config(text="Error emptying Recycle Bin")
            messagebox.showerror("Recycle Bin Error", f"An error occurred:\n{e}")

        self.set_buttons_state("normal")
        self.is_cleaning = False

    def start_dns_cleanup_thread(self, event=None):
        if self.is_cleaning:
            return

        self.is_cleaning = True
        self.set_buttons_state("disabled")
        self.progress_bar["value"] = 0

        threading.Thread(target=self.run_dns_cleanup_process, daemon=True).start()

    def run_dns_cleanup_process(self):
        self.log("[+] Flushing DNS Cache...")
        self.status_label.config(text="Flushing DNS Cache...")
        self.progress_bar["value"] = 30

        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                creationflags=creationflags
            )

            self.progress_bar["value"] = 100

            if result.returncode == 0:
                self.log("[✓] DNS Cache flushed successfully.")
                self.status_label.config(text="DNS Cache flushed successfully")
                messagebox.showinfo("DNS Cache", "DNS Cache flushed successfully.")
            else:
                err_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
                self.log(f"[!] Failed to flush DNS Cache: {err_msg}")
                self.status_label.config(text="Failed to flush DNS Cache")
                messagebox.showerror("DNS Cache Error", f"Failed to flush DNS Cache:\n{err_msg}")

        except Exception as e:
            self.progress_bar["value"] = 100
            self.log(f"[!] Exception occurred while flushing DNS Cache: {e}")
            self.status_label.config(text="Error flushing DNS Cache")
            messagebox.showerror("DNS Cache Error", f"An error occurred:\n{e}")

        self.set_buttons_state("normal")
        self.is_cleaning = False

    def open_disk_cleanup(self, event=None):
        self.log("[+] Launching Windows Disk Cleanup (cleanmgr.exe)...")
        try:
            subprocess.Popen(["cleanmgr.exe", "/sagerun:1"], shell=True)
            self.log("[✓] Windows Disk Cleanup tool opened successfully.")
        except Exception as e:
            try:
                subprocess.Popen(["cleanmgr.exe"], shell=True)
                self.log("[✓] Windows Disk Cleanup tool opened in standard mode.")
            except Exception as ex:
                self.log(f"[!] Failed to launch cleanmgr.exe: {ex}")
                messagebox.showerror("Error", f"Could not launch Windows Disk Cleanup:\n{ex}")

    def on_exit(self):
        if self.is_cleaning:
            if not messagebox.askyesno("Exit Confirmation", "Cleanup is currently in progress. Are you sure you want to exit?"):
                return
        self.root.destroy()


if __name__ == "__main__":
    hide_console()

    if not is_admin():
        run_as_admin()

    root = tk.Tk()
    app = CacheCleanerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_exit)
    root.mainloop()
