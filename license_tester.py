# license_tester.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sv_ttk
import os
from keygen_lock import HardwareLicense, get_hardware_id
import base64, json

"""
Improved tester:
- If license.key is missing, looks for any .key file in the script folder and uses the first one (shows path).
- After a successful verification, writes the verified key to license.key in the tester folder (persistence).
- Includes a debug 'Inspect' button that decodes the token and shows the actual payload (product, exp, users, hwid).
"""

APP_LICENSE_FILENAME = "license.key"   # file tester expects in its folder

class LicenseTester(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("License Tester - ChronoTime Demo (fixed)")
        self.geometry("650x420")
        sv_ttk.use_dark_theme()
        self.verifier = HardwareLicense()
        self.last_used_path = None
        self.create_ui()
        self.check_license_file()

    def create_ui(self):
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="ChronoTime License Tester", font=("Segoe UI", 14, "bold")).pack(pady=6)

        self.status_label = ttk.Label(frame, text="", font=("Segoe UI", 11, "bold"))
        self.status_label.pack(pady=6)

        btn_row = ttk.Frame(frame)
        btn_row.pack(pady=6)
        ttk.Button(btn_row, text="Load .key File", command=self.load_key_file).grid(row=0, column=0, padx=6)
        ttk.Button(btn_row, text="Paste License Key", command=self.paste_key_dialog).grid(row=0, column=1, padx=6)
        ttk.Button(btn_row, text="Inspect .key", command=self.inspect_key_dialog).grid(row=0, column=2, padx=6)
        ttk.Button(btn_row, text="Recheck License", command=self.check_license_file).grid(row=0, column=3, padx=6)

        info_frame = ttk.LabelFrame(frame, text="License Info / HWID")
        info_frame.pack(fill="both", expand=True, pady=10)

        self.info_box = tk.Text(info_frame, height=14, wrap="word", state="disabled")
        self.info_box.pack(fill="both", expand=True, padx=6, pady=6)

        # show where it expects license
        ttk.Label(frame, text=f"Tester looks for: {os.path.abspath(APP_LICENSE_FILENAME)}", font=("Segoe UI", 8)).pack()

    # -------------------------
    #  License checks
    # -------------------------
    def check_license_file(self):
        """Checks for license.key in current folder and verifies it.
        If missing, try to find any .key file in folder and use that (and show path).
        """
        license_path = APP_LICENSE_FILENAME
        if not os.path.exists(license_path):
            # search for any .key file in this folder
            folder = os.path.dirname(os.path.abspath(__file__))
            key_files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".key")]
            if key_files:
                license_path = key_files[0]
                self.last_used_path = license_path
                msg = f"No '{APP_LICENSE_FILENAME}' found. Using first .key in folder:\n{license_path}"
                self.update_status("Using .key found in folder", msg, "orange")
            else:
                hwid = get_hardware_id()
                msg = (f"No license found.\n\nHardware ID for this PC:\n{hwid}\n\n"
                       f"Send this HWID to your software provider to get a license.")
                self.update_status("⚠️ License missing", msg, "orange")
                return

        # read and verify
        try:
            with open(license_path, "r") as f:
                key = f.read().strip()
        except Exception as e:
            self.update_status("❌ Error", f"Failed to open key file: {e}", "red")
            return

        # attempt verify
        self.verify_license(key, save_on_success=True, source_path=license_path)

    def load_key_file(self):
        """Manually choose a .key file for verification."""
        path = filedialog.askopenfilename(filetypes=[("License Key Files", "*.key"), ("All Files", "*.*")])
        if not path:
            return
        with open(path, "r") as f:
            key = f.read().strip()
        self.verify_license(key, save_on_success=True, source_path=path)

    def paste_key_dialog(self):
        """Paste a license directly into a text box for testing."""
        win = tk.Toplevel(self)
        win.title("Paste License Key")
        win.geometry("540x320")
        ttk.Label(win, text="Paste your license key below:").pack(anchor="w", padx=10, pady=6)
        txt = tk.Text(win, height=10, wrap="word")
        txt.pack(fill="both", padx=10, pady=6)

        def verify_paste():
            key = txt.get("1.0", "end").strip()
            if not key:
                messagebox.showwarning("Empty", "Please paste a license key first.")
                return
            self.verify_license(key, save_on_success=False)
            win.destroy()

        ttk.Button(win, text="Verify", command=verify_paste).pack(pady=8)

    def inspect_key_dialog(self):
        """Ask user to pick a key and decode it (show payload)."""
        path = filedialog.askopenfilename(title="Choose .key to inspect", filetypes=[("Key files", "*.key"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r") as f:
                token = f.read().strip()
            payload = self.decode_token_payload(token)
            if not payload:
                messagebox.showerror("Inspect Failed", "Could not decode token (invalid format).")
                return
            pretty = json.dumps(payload, indent=2)
            win = tk.Toplevel(self)
            win.title("Inspect .key payload")
            txt = tk.Text(win, height=16, wrap="word")
            txt.pack(fill="both", expand=True, padx=8, pady=8)
            txt.insert("1.0", pretty)
            txt.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to inspect key: {e}")

    def decode_token_payload(self, token):
        """Try to decode base64 payload and return JSON payload (without checking signature)."""
        try:
            raw = base64.urlsafe_b64decode(token.encode())
            parts = raw.split(b".")
            if len(parts) != 2:
                return None
            payload_bytes = parts[0]
            payload = json.loads(payload_bytes.decode())
            return payload
        except Exception:
            return None

    def verify_license(self, key, save_on_success=False, source_path=None):
        """Core verification logic."""
        res = self.verifier.verify_license(key, grace_days=7)

        if not res["valid"]:
            # fully invalid (signature/hwid/expired beyond grace)
            self.update_status("❌ INVALID", res.get("reason", "Invalid license"), "red")
            return

        info = res.get("info", {})
        if res.get("grace"):
            msg = (f"License expired on {info.get('exp')}.\n"
                   f"Grace period active: {res.get('days_left')} day(s) remaining.\n\n"
                   f"Product: {info.get('product')}\nHWID: {info.get('hwid')}\nUsers: {info.get('users')}")
            self.update_status("⚠️ EXPIRED (Grace Active)", msg, "orange")
        else:
            msg = (f"License valid for: {info.get('product')}\n"
                   f"Expires: {info.get('exp')}  ({res.get('days_left')} day(s) left)\n"
                   f"Max users: {info.get('users')}\n"
                   f"HWID: {info.get('hwid')}")
            self.update_status("✅ LICENSE VALID", msg, "green")

        # If verified OK and asked to save, write to license.key so it persists across restarts
        if save_on_success:
            try:
                with open(APP_LICENSE_FILENAME, "w") as f:
                    f.write(key)
                # remember which file we used
                self.last_used_path = source_path or APP_LICENSE_FILENAME
                # show explicit message about where it was saved
                self.info_box.config(state="normal")
                self.info_box.insert("end", f"\n\nSaved verified key to: {os.path.abspath(APP_LICENSE_FILENAME)}")
                self.info_box.config(state="disabled")
            except Exception as e:
                messagebox.showwarning("Save failed", f"Verified but failed to save license.key: {e}")

    def update_status(self, title, message, color):
        """Updates the status bar and info box."""
        self.status_label.config(text=title, foreground=color)
        self.info_box.config(state="normal")
        self.info_box.delete("1.0", "end")
        self.info_box.insert("1.0", message)
        self.info_box.config(state="disabled")


if __name__ == "__main__":
    import json
    app = LicenseTester()
    app.mainloop()
