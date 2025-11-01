"""
license_gui_v6.py
------------------------
Offline License Generator with GUI (Tkinter + SQLite)

Features:
    • License creation, renewal, and validation (offline)
    • Local SQLite license database
    • Copy / Export / Email license keys
    • Verify licenses (.key files)
    • Dark theme using sv_ttk

Compatible with:
    - keygen_lock.py  (for license generation)
    - license_store.py (for SQLite storage)

To use:
    python license_gui_v6.py

Developers:
    Replace or configure your own SMTP credentials for email sending.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import smtplib, ssl, os, datetime
from email.message import EmailMessage
import sv_ttk, pyperclip

from keygen_lock import HardwareLicense, get_hardware_id
from license_store import init_db, save_license, fetch_all, search

DB_FILE = "licenses.db"


class LicenseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Python Offline License Generator")
        self.geometry("1040x620")
        sv_ttk.use_dark_theme()
        init_db()
        self.create_widgets()
        self.load_table()

    # ---------------------------
    #  GUI Setup
    # ---------------------------
    def create_widgets(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        # --- Input Fields ---
        labels = ["Client / Company:", "Product:", "Expiry (YYYY-MM-DD):", "Max Users:", "HWID:"]
        self.entries = {}

        default_values = {
            "Expiry (YYYY-MM-DD):": (datetime.date.today() + datetime.timedelta(days=365)).isoformat(),
            "Max Users:": "5",
            "HWID:": get_hardware_id(),
        }

        for i, label in enumerate(labels):
            ttk.Label(top, text=label).grid(row=i, column=0, sticky="e")
            entry = ttk.Entry(top, width=35)
            entry.grid(row=i, column=1, padx=5, pady=3)
            if label in default_values:
                entry.insert(0, default_values[label])
            self.entries[label] = entry

        # --- Buttons ---
        btn_frame = ttk.Frame(top)
        btn_frame.grid(row=0, column=2, rowspan=6, padx=15)
        buttons = [
            ("Generate", self.generate_license),
            ("Renew License", self.renew_license),
            ("Copy Selected", self.copy_selected),
            ("Export .key", self.export_selected),
            ("Send via Email", self.send_license_email),
            ("Verify .key", self.verify_key_dialog),
            ("Refresh", self.load_table),
            ("Clear Fields", self.clear_fields),
        ]
        for text, cmd in buttons:
            ttk.Button(btn_frame, text=text, command=cmd).pack(fill="x", pady=3)

        # --- Search ---
        ttk.Label(top, text="Search:").grid(row=6, column=0, sticky="e")
        self.search_entry = ttk.Entry(top, width=35)
        self.search_entry.grid(row=6, column=1, padx=5, pady=8)
        ttk.Button(top, text="Find", command=self.search_table).grid(row=6, column=2, padx=5)

        # --- Table ---
        columns = (
            "id", "client_name", "product", "license_key", "expiry_date",
            "max_users", "hwid", "date_generated"
        )
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=14)

        headers = {
            "id": "ID", "client_name": "Client", "product": "Product",
            "license_key": "License Key", "expiry_date": "Expiry", "max_users": "Users",
            "hwid": "HWID", "date_generated": "Generated"
        }
        widths = {"id": 50, "client_name": 150, "product": 120, "license_key": 320,
                  "expiry_date": 100, "max_users": 80, "hwid": 150, "date_generated": 110}

        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col])

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)

    # ---------------------------
    #  Data & Form Handlers
    # ---------------------------
    def clear_fields(self):
        for e in self.entries.values():
            e.delete(0, "end")

    def on_row_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        if len(vals) < 8:
            return
        _, client, product, _, expiry, users, hwid, _ = vals
        fields = [
            ("Client / Company:", client),
            ("Product:", product),
            ("Expiry (YYYY-MM-DD):", expiry),
            ("Max Users:", users),
            ("HWID:", hwid),
        ]
        for label, value in fields:
            e = self.entries[label]
            e.delete(0, "end")
            e.insert(0, value)

    # ---------------------------
    #  Database Operations
    # ---------------------------
    def load_table(self, search_text=None):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = search(search_text) if search_text else fetch_all()
        for row in rows:
            self.tree.insert("", "end", values=row)

    def search_table(self):
        term = self.search_entry.get().strip()
        self.load_table(term if term else None)

    # ---------------------------
    #  License Operations
    # ---------------------------
    def generate_license(self):
        client = self.entries["Client / Company:"].get().strip()
        product = self.entries["Product:"].get().strip()
        expiry = self.entries["Expiry (YYYY-MM-DD):"].get().strip()
        users = self.entries["Max Users:"].get().strip()
        hwid = self.entries["HWID:"].get().strip()

        if not all([client, product, expiry, users, hwid]):
            messagebox.showwarning("Missing info", "Please fill in all fields.")
            return
        try:
            users = int(users)
        except ValueError:
            messagebox.showwarning("Invalid", "User count must be numeric.")
            return

        gen = HardwareLicense()
        key = gen.generate_license(product, expiry, users, hwid)
        save_license(client, product, key, expiry, users, hwid)
        messagebox.showinfo("License Generated", f"✅ Saved!\nClient: {client}\nKey:\n{key}")
        self.load_table()

    def renew_license(self):
        lic = self.get_selected_license()
        if not lic:
            return
        new_exp = simpledialog.askstring(
            "Renew License",
            f"Renew {lic['client_name']} (current expiry: {lic['expiry_date']})\nEnter new expiry (YYYY-MM-DD):"
        )
        if not new_exp:
            return
        try:
            datetime.datetime.strptime(new_exp, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid", "Must be YYYY-MM-DD.")
            return

        gen = HardwareLicense()
        new_key = gen.generate_license(lic["product"], new_exp, int(lic["max_users"]), lic["hwid"])
        save_license(lic["client_name"], lic["product"], new_key, new_exp, int(lic["max_users"]), lic["hwid"])
        messagebox.showinfo("Renewed", f"✅ License renewed!\nNew expiry: {new_exp}")
        self.load_table()

    # ---------------------------
    #  Copy / Export / Verify
    # ---------------------------
    def get_selected_license(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Please select a license first.")
            return None
        vals = self.tree.item(sel[0], "values")
        keys = ("id", "client_name", "product", "license_key", "expiry_date", "max_users", "hwid", "date_generated")
        return dict(zip(keys, vals))

    def copy_selected(self):
        lic = self.get_selected_license()
        if lic:
            pyperclip.copy(lic["license_key"])
            messagebox.showinfo("Copied", "License key copied to clipboard.")

    def export_selected(self):
        lic = self.get_selected_license()
        if not lic:
            return
        default_name = f"{lic['client_name']}_{lic['product']}.key".replace(" ", "_")
        path = filedialog.asksaveasfilename(defaultextension=".key", initialfile=default_name,
                                            filetypes=[("License Key Files", "*.key"), ("All Files", "*.*")])
        if path:
            with open(path, "w") as f:
                f.write(lic["license_key"])
            messagebox.showinfo("Exported", f"Saved to:\n{path}")

    def verify_key_dialog(self):
        win = tk.Toplevel(self)
        win.title("Verify License Key")
        win.geometry("650x300")
        ttk.Label(win, text="Paste or load license key:").pack(anchor="w", padx=10, pady=5)
        text = tk.Text(win, height=6, wrap="word")
        text.pack(fill="both", expand=False, padx=10)
        result_label = ttk.Label(win, text="", font=("Segoe UI", 10, "bold"))
        result_label.pack(pady=8)

        def load_file():
            path = filedialog.askopenfilename(filetypes=[("License Key Files", "*.key"), ("All Files", "*.*")])
            if path:
                with open(path) as f:
                    text.delete("1.0", "end")
                    text.insert("1.0", f.read().strip())

        def do_verify():
            token = text.get("1.0", "end").strip()
            if not token:
                messagebox.showwarning("Empty", "Paste or load key first.")
                return
            gen = HardwareLicense()
            res = gen.verify_license(token, grace_days=7)
            if res.get("valid"):
                info = res.get("info", {})
                if res.get("grace"):
                    clr, status = "#FFD966", "⚠️  EXPIRED (Grace)"
                    msg = f"Expired {info['exp']} — {res['days_left']} day(s) grace left"
                else:
                    clr, status = "#A9DFBF", "✅ VALID"
                    msg = f"{info['product']} — {res['days_left']} day(s) left"
            else:
                clr, status = "#F5B7B1", "❌ INVALID"
                msg = res.get("reason", "Unknown error")
            result_label.config(text=f"{status}\n{msg}", background=clr)

        btns = ttk.Frame(win)
        btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="Load .key", command=load_file).pack(side="left", padx=5)
        ttk.Button(btns, text="Verify", command=do_verify).pack(side="left", padx=5)
        ttk.Button(btns, text="Close", command=win.destroy).pack(side="right", padx=5)

    # ---------------------------
    #  Email Sending
    # ---------------------------
    def send_license_email(self):
        lic = self.get_selected_license()
        if not lic:
            return

        tmp_path = f"{lic['client_name']}_{lic['product']}.key".replace(" ", "_")
        with open(tmp_path, "w") as f:
            f.write(lic["license_key"])

        win = tk.Toplevel(self)
        win.title("Send License via Email")
        win.geometry("420x320")
        ttk.Label(win, text="Recipient Email:").pack(anchor="w", padx=8, pady=5)
        email_entry = ttk.Entry(win, width=40)
        email_entry.pack(padx=8)

        ttk.Label(win, text="Message (optional):").pack(anchor="w", padx=8, pady=5)
        msg_box = tk.Text(win, height=6, wrap="word")
        msg_box.insert("1.0", f"Dear {lic['client_name']},\n\nPlease find attached your license key for {lic['product']}.\n\nRegards,\nYour Company")
        msg_box.pack(fill="x", padx=8, pady=5)

        ttk.Label(win, text="SMTP Sender (your email):").pack(anchor="w", padx=8, pady=5)
        sender_entry = ttk.Entry(win, width=40)
        sender_entry.insert(0, "")
        sender_entry.pack(padx=8)

        ttk.Label(win, text="App Password:").pack(anchor="w", padx=8, pady=5)
        pass_entry = ttk.Entry(win, width=40, show="*")
        pass_entry.pack(padx=8)

        def send_now():
            recipient = email_entry.get().strip()
            sender = sender_entry.get().strip()
            pwd = pass_entry.get().strip()
            msg_body = msg_box.get("1.0", "end").strip()

            if not all([recipient, sender, pwd]):
                messagebox.showwarning("Missing Info", "Please fill in all required fields.")
                return

            try:
                msg = EmailMessage()
                msg["Subject"] = f"License Key for {lic['product']}"
                msg["From"] = sender
                msg["To"] = recipient
                msg.set_content(msg_body)

                with open(tmp_path, "rb") as f:
                    msg.add_attachment(
                        f.read(),
                        maintype="application",
                        subtype="octet-stream",
                        filename=os.path.basename(tmp_path)
                    )

                context = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                    server.login(sender, pwd)
                    server.send_message(msg)

                messagebox.showinfo("Email Sent", f"✅ License sent to {recipient}")
                win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send email:\n{e}")

        ttk.Button(win, text="Send Email", command=send_now).pack(pady=10)


if __name__ == "__main__":
    app = LicenseApp()
    app.mainloop()
