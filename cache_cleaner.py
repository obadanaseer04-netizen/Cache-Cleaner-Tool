import os
import sys
import shutil
import pathlib
import threading
import queue
import ctypes
import time
import tkinter as tk
from tkinter import ttk, messagebox

# Hide Console Window on Windows if running via python.exe / executable
def hide_console():
    try:
        # Get handle to current console window and hide it
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd != 0:
            ctypes.windll.user32.ShowWindow(hwnd, 0) # 0 = SW_HIDE
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
            # Determine the executable to run
            # If running as script, use pythonw.exe to prevent CMD window popup
            if getattr(sys, 'frozen', False):
                executable = sys.executable
                args = " ".join(f'"{arg}"' for arg in sys.argv[1:])
            else:
                # Replace python.exe with pythonw.exe if available
                python_exe = sys.executable
                if python_exe.endswith("python.exe"):
                    pythonw = python_exe[:-10] + "pythonw.exe"
                    if os.path.exists(pythonw):
                        python_exe = pythonw
                executable = python_exe
                args = " ".join(f'"{arg}"' for arg in sys.argv)

            # Re-run script with UAC admin request
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
        self.root.geometry("680x620")
        self.root.minsize(600, 550)
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
        self.success_color = "#a6e3a1"
        self.muted_color = "#6c7086"

        # Style Progressbar
        self.style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor="#313244",
            background=self.accent_color,
            thickness=12,
            borderwidth=0
        )

    def build_ui(self):
        # Header Section
        header_frame = tk.Frame(self.root, bg=self.bg_color)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title_label = tk.Label(
            header_frame, text="Windows Cache Cleaner",
            font=("Segoe UI", 18, "bold"), fg=self.text_color, bg=self.bg_color
        )
        title_label.pack(anchor="w")

        subtitle_label = tk.Label(
            header_frame, text="Clean temporary files safely and quickly",
            font=("Segoe UI", 10), fg=self.muted_color, bg=self.bg_color
        )
        subtitle_label.pack(anchor="w")

        # Admin status badge
        admin_text = "🛡️ Admin Privileges: Active" if is_admin() else "⚠️ Standard User (Limited Prefetch access)"
        admin_color = self.success_color if is_admin() else "#f9e2af"
        admin_label = tk.Label(
            header_frame, text=admin_text,
            font=("Segoe UI", 9, "bold"), fg=admin_color, bg=self.bg_color
        )
        admin_label.pack(anchor="w", pady=(4, 0))

        # Action Section (CLEAN Button)
        action_frame = tk.Frame(self.root, bg=self.bg_color)
        action_frame.pack(fill="x", padx=20, pady=10)

        self.clean_btn = tk.Button(
            action_frame, text="CLEAN", font=("Segoe UI", 14, "bold"),
            bg=self.accent_color, fg="#11111b", activebackground=self.accent_hover,
            activeforeground="#11111b", bd=0, relief="flat", cursor="hand2",
            command=self.start_cleanup_thread, pady=10
        )
        self.clean_btn.pack(fill="x")

        # Progress Section
        progress_frame = tk.Frame(self.root, bg=self.bg_color)
        progress_frame.pack(fill="x", padx=20, pady=5)

        self.status_label = tk.Label(
            progress_frame, text="Ready", font=("Segoe UI", 10),
            fg=self.text_color, bg=self.bg_color
        )
        self.status_label.pack(anchor="w", pady=(0, 5))

        self.progress_bar = ttk.Progressbar(
            progress_frame, style="Custom.Horizontal.TProgressbar",
            orient="horizontal", mode="determinate"
        )
        self.progress_bar.pack(fill="x")

        # Statistics Dashboard
        stats_frame = tk.Frame(self.root, bg=self.card_color, bd=1, relief="solid")
        stats_frame.pack(fill="x", padx=20, pady=15)

        # Config layout grid inside dashboard
        for i in range(4):
            stats_frame.columnconfigure(i, weight=1)

        self.lbl_files = self.create_stat_box(stats_frame, "Files Deleted", "0", 0)
        self.lbl_folders = self.create_stat_box(stats_frame, "Folders Deleted", "0", 1)
        self.lbl_skipped = self.create_stat_box(stats_frame, "Skipped", "0", 2)
        self.lbl_space = self.create_stat_box(stats_frame, "Space Freed", "0 B", 3)

        # Activity Log Section
        log_frame = tk.Frame(self.root, bg=self.bg_color)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        log_title = tk.Label(
            log_frame, text="Activity Log", font=("Segoe UI", 10, "bold"),
            fg=self.text_color, bg=self.bg_color
        )
        log_title.pack(anchor="w", pady=(0, 5))

        self.log_text = tk.Text(
            log_frame, bg="#11111b", fg=self.text_color, font=("Consolas", 9),
            bd=0, relief="flat", state="disabled", wrap="word"
        )
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview, bg=self.card_color)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        # Footer Buttons
        footer_frame = tk.Frame(self.root, bg=self.bg_color)
        footer_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.clear_log_btn = tk.Button(
            footer_frame, text="CLEAR LOG", font=("Segoe UI", 9, "bold"),
            bg="#313244", fg=self.text_color, activebackground="#45475a",
            activeforeground=self.text_color, bd=0, relief="flat", cursor="hand2",
            command=self.clear_log, padx=15, pady=5
        )
        self.clear_log_btn.pack(side="left")

        self.exit_btn = tk.Button(
            footer_frame, text="EXIT", font=("Segoe UI", 9, "bold"),
            bg="#313244", fg=self.danger_color, activebackground="#45475a",
            activeforeground=self.danger_color, bd=0, relief="flat", cursor="hand2",
            command=self.on_exit, padx=15, pady=5
        )
        self.exit_btn.pack(side="right")

    def create_stat_box(self, parent, title, initial_val, col):
        frame = tk.Frame(parent, bg=self.card_color, pady=10)
        frame.grid(row=0, column=col, sticky="nsew")

        val_lbl = tk.Label(
            frame, text=initial_val, font=("Segoe UI", 12, "bold"),
            fg=self.accent_color, bg=self.card_color
        )
        val_lbl.pack()

        title_lbl = tk.Label(
            frame, text=title, font=("Segoe UI", 8),
            fg=self.muted_color, bg=self.card_color
        )
        title_lbl.pack()

        return val_lbl

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

    def start_cleanup_thread(self):
        if self.is_cleaning:
            return
        
        self.is_cleaning = True
        self.clean_btn.config(state="disabled", text="Cleaning...", bg="#45475a")
        self.progress_bar["value"] = 0
        
        threading.Thread(target=self.run_cleanup_process, daemon=True).start()

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

    def run_cleanup_process(self):
        self.log("[+] Starting cleanup process...")
        
        total_files_deleted = 0
        total_folders_deleted = 0
        total_skipped = 0
        total_bytes_freed = 0

        target_dirs = self.get_target_directories()
        step_increment = 100 / max(len(target_dirs), 1)

        for idx, (label, dir_path) in enumerate(target_dirs):
            self.status_label.config(text=f"Cleaning {label}...")
            self.log(f"[+] Processing directory {label}: {dir_path}")

            if not dir_path.exists() or not dir_path.is_dir():
                self.log(f"[!] Path does not exist or is inaccessible: {dir_path}")
                self.progress_bar["value"] = (idx + 1) * step_increment
                continue

            files_del, flds_del, skipped, bytes_freed = self.clean_single_directory(dir_path)
            
            total_files_deleted += files_del
            total_folders_deleted += flds_del
            total_skipped += skipped
            total_bytes_freed += bytes_freed

            self.progress_bar["value"] = (idx + 1) * step_increment
            
            # Update UI statistics dynamically
            self.lbl_files.config(text=str(total_files_deleted))
            self.lbl_folders.config(text=str(total_folders_deleted))
            self.lbl_skipped.config(text=str(total_skipped))
            self.lbl_space.config(text=self.format_size(total_bytes_freed))

        # Completion Phase
        self.status_label.config(text="Cleaning completed")
        self.log("[✓] Cleanup completed successfully!")
        self.log(f"    Summary: {total_files_deleted} Files Deleted, {total_folders_deleted} Folders Deleted, {total_skipped} Skipped, {self.format_size(total_bytes_freed)} Freed.")

        # Re-enable button
        self.clean_btn.config(state="normal", text="CLEAN", bg=self.accent_color)
        self.is_cleaning = False

        messagebox.showinfo(
            "Cleanup Completed!",
            f"Your temporary files have been cleaned.\n\n"
            f"• Files Deleted: {total_files_deleted}\n"
            f"• Folders Deleted: {total_folders_deleted}\n"
            f"• Space Freed: {self.format_size(total_bytes_freed)}\n"
            f"• Files Skipped: {total_skipped}"
        )

    def clean_single_directory(self, folder_path):
        files_deleted = 0
        folders_deleted = 0
        skipped = 0
        bytes_freed = 0

        try:
            entries = list(folder_path.iterdir())
        except Exception as e:
            self.log(f"[!] Error accessing folder {folder_path}: {e}")
            return files_deleted, folders_deleted, 1, bytes_freed

        for entry in entries:
            try:
                if entry.is_file() or entry.is_symlink():
                    try:
                        file_size = entry.stat().st_size
                    except Exception:
                        file_size = 0

                    try:
                        entry.unlink()
                        files_deleted += 1
                        bytes_freed += file_size
                        self.log(f"[+] Deleted file: {entry.name}")
                    except (PermissionError, OSError):
                        skipped += 1
                        self.log(f"[!] Skipped file (in use/locked): {entry.name}")

                elif entry.is_dir():
                    sub_f_del, sub_fld_del, sub_skip, sub_bytes = self.clean_sub_directory(entry)
                    files_deleted += sub_f_del
                    folders_deleted += sub_fld_del
                    skipped += sub_skip
                    bytes_freed += sub_bytes

                    try:
                        entry.rmdir()
                        folders_deleted += 1
                        self.log(f"[+] Deleted folder: {entry.name}")
                    except (PermissionError, OSError):
                        pass

            except Exception as e:
                skipped += 1
                self.log(f"[!] Error deleting {entry.name}: {e}")

        return files_deleted, folders_deleted, skipped, bytes_freed

    def clean_sub_directory(self, folder_path):
        files_deleted = 0
        folders_deleted = 0
        skipped = 0
        bytes_freed = 0

        try:
            for root, dirs, files in os.walk(folder_path, topdown=False):
                for f in files:
                    fp = pathlib.Path(root) / f
                    try:
                        file_size = fp.stat().st_size
                    except Exception:
                        file_size = 0

                    try:
                        fp.unlink()
                        files_deleted += 1
                        bytes_freed += file_size
                    except (PermissionError, OSError):
                        skipped += 1

                for d in dirs:
                    dp = pathlib.Path(root) / d
                    try:
                        dp.rmdir()
                        folders_deleted += 1
                    except (PermissionError, OSError):
                        pass
        except Exception:
            pass

        return files_deleted, folders_deleted, skipped, bytes_freed

    def on_exit(self):
        if self.is_cleaning:
            if not messagebox.askyesno("Exit Confirmation", "Cleanup is currently in progress. Are you sure you want to exit?"):
                return
        self.root.destroy()


if __name__ == "__main__":
    # Hide any existing console window immediately upon launch
    hide_console()

    # Elevate to administrator automatically if needed
    if not is_admin():
        run_as_admin()

    root = tk.Tk()
    app = CacheCleanerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_exit)
    root.mainloop()