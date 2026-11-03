"""Save the Gemini API key and reviewer access code into .streamlit/secrets.toml.

Run:  pyw set_secrets.py --window   (a small window with masked boxes; easiest)
  or: py set_secrets.py             (hidden typing in the terminal)
The key never shows on screen or in terminal history. The file it writes is git-ignored.
"""
import getpass
import json
import sys
from pathlib import Path

SECRETS = Path(__file__).parent / ".streamlit" / "secrets.toml"


def save(key: str, code: str, path: Path = SECRETS, model: str = "gemini-3.5-flash-lite", limit: int = 20):
    # json.dumps gives a correctly escaped TOML basic string
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        "# Private: never commit, zip or share this file.\n"
        f"GEMINI_API_KEY = {json.dumps(key)}\n"
        f"GEMINI_MODEL = {json.dumps(model)}\n"
        f"ACCESS_CODE = {json.dumps(code)}\n"
        f"DAILY_LIMIT = {int(limit)}\n",
        encoding="utf-8",
    )


def problem(key: str, code: str) -> str:
    if len(key) < 20 or " " in key or key.startswith("your-key"):
        return "That does not look like a Gemini key. Copy it again from aistudio.google.com (Get API key)."
    if len(code) < 6 or code == "choose-a-code":
        return "Choose an access code of at least 6 characters."
    return ""


def window(selftest: bool = False):
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("Save Gemini key (private)")
    root.resizable(False, False)
    tk.Label(root, text="1. Paste your Gemini API key (from aistudio.google.com > Get API key):",
             anchor="w").grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 2))
    key_box = tk.Entry(root, show="•", width=48)
    key_box.grid(row=1, column=0, padx=(12, 4), pady=2)

    def paste():
        try:
            key_box.delete(0, "end")
            key_box.insert(0, root.clipboard_get().strip())
        except tk.TclError:
            messagebox.showerror("Nothing to paste", "Copy the key in AI Studio first, then click Paste.")

    tk.Button(root, text="Paste from clipboard", command=paste).grid(row=1, column=1, padx=(0, 12))
    tk.Label(root, text="2. Choose an access code for reviewers (6+ letters/numbers):",
             anchor="w").grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 2))
    code_box = tk.Entry(root, show="•", width=48)
    code_box.grid(row=3, column=0, padx=(12, 4), pady=2)
    shown = tk.BooleanVar(value=False)
    tk.Checkbutton(root, text="Show code", variable=shown,
                   command=lambda: code_box.config(show="" if shown.get() else "•")).grid(row=3, column=1, sticky="w")

    def save_clicked():
        key, code = key_box.get().strip(), code_box.get().strip()
        error = problem(key, code)
        if error:
            messagebox.showerror("Not saved", error)
            return
        save(key, code)
        root.clipboard_clear()  # do not leave the key on the clipboard
        messagebox.showinfo("Saved", f"Saved privately.\nKey: {key[:4]}... ({len(key)} characters)\n"
                                     f"Access code: {len(code)} characters\n\nThe clipboard was cleared.")
        root.destroy()

    tk.Button(root, text="3. Save", width=14, command=save_clicked).grid(row=4, column=0, columnspan=2, pady=12)
    root.attributes("-topmost", True)
    if selftest:
        root.update()
        print("window OK")
        root.destroy()
        return
    root.mainloop()


def main():
    if "--window" in sys.argv or "--selftest" in sys.argv:
        window(selftest="--selftest" in sys.argv)
        return
    print("Paste your Gemini API key and press Enter (nothing will show while you paste).")
    key = getpass.getpass("Gemini API key: ").strip()
    if len(key) < 20 or " " in key or key.startswith("your-key"):
        print("That does not look like a Gemini key. Nothing was saved; run this again.")
        return
    code = getpass.getpass("Choose an access code for reviewers (at least 6 characters): ").strip()
    if len(code) < 6 or code == "choose-a-code":
        print("Access code is too short or still the example. Nothing was saved; run this again.")
        return
    if getpass.getpass("Type the access code again: ").strip() != code:
        print("The access codes did not match. Nothing was saved; run this again.")
        return
    save(key, code)
    print(f"Saved. Key: {key[:4]}... ({len(key)} characters). Access code: {len(code)} characters.")
    print(f"File: {SECRETS}")


if __name__ == "__main__":
    main()
