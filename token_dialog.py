"""Native Windows paste-friendly enrollment dialog for the Meta User token.

All token handling stays in this process; only ciphertext leaves process memory.
No clipboard reads unless the user clicks Paste or performs a paste shortcut.
"""
from __future__ import annotations

from secret_store import TokenStoreError, read_meta_user_token, save_meta_user_token


def enroll_gui() -> bool:
    try:
        import tkinter as tk
        from tkinter import messagebox, ttk
    except ImportError as exc:
        raise TokenStoreError(
            "Không có giao diện Tkinter. Hãy cài Python có Tkinter."
        ) from None

    try:
        root = tk.Tk()
    except tk.TclError:
        raise TokenStoreError(
            "Không thể mở cửa sổ nhập token. Hãy chạy trực tiếp trên Desktop Windows."
        ) from None

    root.title("VOIDSCAN · Kết nối Meta")
    root.configure(background="#f5f6fa")
    root.geometry("590x330")
    root.minsize(480, 290)
    root.resizable(True, False)
    try:
        root.iconbitmap(default="")
    except (tk.TclError, OSError):
        pass

    # Center without depending on a particular monitor size.
    root.update_idletasks()
    x = max(0, (root.winfo_screenwidth() - 590) // 2)
    y = max(0, (root.winfo_screenheight() - 330) // 2)
    root.geometry(f"590x330+{x}+{y}")

    body = ttk.Frame(root, padding=(28, 20, 28, 22))
    body.pack(fill="both", expand=True)
    ttk.Label(body, text="Kết nối VOIDSCAN với Meta",
              font=("Segoe UI", 17, "bold")).pack(anchor="w")
    ttk.Label(body, text="Dán User Access Token một lần; VOIDSCAN sẽ mã hóa bằng Windows DPAPI.",
              wraplength=530, font=("Segoe UI", 10)).pack(anchor="w", pady=(6, 17))
    ttk.Label(body, text="Meta User Access Token",
              font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))

    token_var = tk.StringVar()
    row = ttk.Frame(body)
    row.pack(fill="x")
    input_box = ttk.Entry(row, textvariable=token_var, show="●",
                          font=("Segoe UI", 12))
    input_box.pack(side="left", expand=True, fill="x", ipady=6)

    notice_var = tk.StringVar(value="Có thể nhấn Ctrl + V, chuột phải → Dán, hoặc nút Dán từ clipboard.")
    status = ttk.Label(body, textvariable=notice_var, wraplength=530, font=("Segoe UI", 10))
    status.pack(fill="x", anchor="w", pady=(10, 5))

    result = {"saved": False}

    def paste_from_clipboard() -> None:
        try:
            value = root.clipboard_get()
        except tk.TclError:
            notice_var.set("Clipboard đang trống hoặc không có văn bản. Hãy sao chép token rồi thử lại.")
            return
        if not value:
            notice_var.set("Clipboard không có văn bản.")
            return
        token_var.set(value.strip())
        notice_var.set("Đã dán token vào ô bảo mật. Kiểm tra và nhấn Lưu token.")
        input_box.focus_set()
        input_box.icursor("end")

    ttk.Button(row, text="Dán từ clipboard", command=paste_from_clipboard).pack(
        side="left", padx=(9, 0), ipady=5
    )

    context_menu = tk.Menu(root, tearoff=False)
    context_menu.add_command(label="Dán (Ctrl+V)", command=paste_from_clipboard)
    context_menu.add_command(label="Xóa ô nhập", command=lambda: token_var.set(""))

    def show_context_menu(event):
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
        return "break"

    input_box.bind("<Button-3>", show_context_menu)
    input_box.bind("<Control-v>", lambda e: (paste_from_clipboard(), "break")[1])
    input_box.bind("<Control-V>", lambda e: (paste_from_clipboard(), "break")[1])

    ttk.Label(body, text="Không gửi token qua chat hoặc commit lên GitHub.",
              font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 16))

    def save() -> None:
        value = token_var.get().strip()
        if not value:
            notice_var.set("Chưa có token. Hãy sao chép từ Graph API Explorer và dán vào ô trên.")
            input_box.focus_set()
            return
        try:
            save_meta_user_token(value)
            if not read_meta_user_token():
                raise TokenStoreError("Không thể xác minh file mã hóa.")
        except TokenStoreError as exc:
            notice_var.set(str(exc))
            return
        except OSError:
            notice_var.set("Không thể ghi token mã hóa. Kiểm tra quyền lưu của Windows.")
            return

        # Only clear clipboard when it still contains the exact secret just stored.
        # Do not wipe a clipboard holding something else.
        try:
            if root.clipboard_get() == value:
                root.clipboard_clear()
                root.update()
        except tk.TclError:
            pass
        token_var.set("")
        result["saved"] = True
        messagebox.showinfo("VOIDSCAN", "Đã lưu token mã hóa thành công.\n"
                            "Từ nay chỉ cần mở VOIDSCAN trên Desktop.", parent=root)
        root.destroy()

    footer = ttk.Frame(body)
    footer.pack(fill="x", side="bottom")
    ttk.Button(footer, text="Hủy", command=root.destroy).pack(side="right", padx=(10, 0))
    ttk.Button(footer, text="Lưu token", command=save).pack(side="right")

    input_box.bind("<Return>", lambda _: save())
    root.bind("<Escape>", lambda _: root.destroy())
    root.after(120, input_box.focus_set)
    root.lift()
    try:
        root.attributes("-topmost", True)
        root.after(700, lambda: root.attributes("-topmost", False))
    except tk.TclError:
        pass
    root.mainloop()
    return result["saved"]
