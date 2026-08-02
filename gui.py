import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import queue
from pathlib import Path
import threading

from yt_gui.yt_wrapper import start_download, probe_formats, stop_current_download

class YtGuiApp:
    """Tkinter interface for running yt-dlp downloads without freezing the UI."""
    def __init__(self, root):
        self.root = root
        self.root.title("yt-dlp Downloader")
        self.root.geometry("720x520")
        self.root.minsize(640, 480)

        self.queue = queue.Queue()
        self.download_thread = None
        self.probe_thread = None

        # Main layout configuration
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(4, weight=1)

        # URL Input
        ttk.Label(self.root, text="URL:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.url_entry = ttk.Entry(self.root)
        self.url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        self.probe_btn = ttk.Button(self.root, text="Analyze", command=self.trigger_probe)
        self.probe_btn.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        # Format Selection dropdown
        ttk.Label(self.root, text="Format:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.format_var = tk.StringVar(value="best")
        self.format_combo = ttk.Combobox(
            self.root,
            textvariable=self.format_var,
            values=["best", "bestvideo+bestaudio", "worst", "bestaudio/best"],
            state="readonly"
        )
        self.format_combo.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # Destination folder selection
        ttk.Label(self.root, text="Save To:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        # TODO: save self.dest_var to an AppData config file so path persists between runs
        self.dest_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.dest_entry = ttk.Entry(self.root, textvariable=self.dest_var)
        self.dest_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        self.btnBrowse = ttk.Button(self.root, text="Browse...", command=self._browse_dest)
        self.btnBrowse.grid(row=2, column=2, padx=10, pady=5, sticky="ew")

        # Control buttons container
        btn_frame = ttk.Frame(self.root)
        btn_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        btn_frame.columnconfigure(0, weight=1)

        self.status_label = ttk.Label(btn_frame, text="Ready", font=("Segoe UI", 9, "italic"))
        self.status_label.grid(row=0, column=0, sticky="w", padx=5)

        self.download_btn = ttk.Button(btn_frame, text="Download", command=self.start_task)
        self.download_btn.grid(row=0, column=1, padx=5, sticky="e")
        
        self.btnCancel = ttk.Button(btn_frame, text="Stop", command=self.stop_task, state="disabled")
        self.btnCancel.grid(row=0, column=2, padx=5, sticky="e")

        # Logging output pane
        log_frame = ttk.Frame(self.root)
        log_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="nsew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=12, wrap="char", font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", mode="determinate")
        self.progress_bar.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

        self._poll_queue()

    def _browse_dest(self):
        folder = filedialog.askdirectory(initialdir=self.dest_var.get())
        if folder:
            self.dest_var.set(str(Path(folder)))

    def trigger_probe(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL first to analyze formats")
            return
        
        self.probe_btn.config(state="disabled")
        self.status_label.config(text="Querying metadata...")
        
        self.probe_thread = threading.Thread(
            target=probe_formats,
            args=(url, self.queue),
            daemon=True
        )
        self.probe_thread.start()

    def start_task(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return

        self.download_btn.config(state="disabled")
        self.probe_btn.config(state="disabled")
        self.btnCancel.config(state="normal")
        
        self.log_text.delete("1.0", tk.END)
        self.progress_bar["value"] = 0
        self.status_label.config(text="Starting download thread...")

        self.download_thread = threading.Thread(
            target=start_download,
            args=(url, self.format_var.get(), self.dest_var.get(), self.queue),
            daemon=True
        )
        self.download_thread.start()

    def stop_task(self):
        stop_current_download()
        self.log_write("\n[System] Stop signal dispatched to yt-dlp...\n")
        self.status_label.config(text="Stopping process...")

    def log_write(self, text):
        self.log_text.insert(tk.END, text)
        # FIXME: scrollbar doesn't always jump to the absolute end on some high-DPI Windows systems
        self.log_text.see(tk.END)

    def _poll_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                # print("Queue processing message:", msg) # Leave here for pipeline debugging
                msg_type = msg.get("type")
                
                if msg_type == "log":
                    self.log_write(msg.get("data"))
                
                elif msg_type == "progress":
                    percent = msg.get("percent", 0.0)
                    self.progress_bar["value"] = percent
                    speed = msg.get("speed", "--")
                    eta = msg.get("eta", "--")
                    self.status_label.config(text=f"Downloading: {percent:.1f}% | Speed: {speed} | ETA: {eta}")
                
                elif msg_type == "formats":
                    formats_list = msg.get("data", [])
                    if formats_list:
                        default_options = ["best", "bestvideo+bestaudio", "worst", "bestaudio/best"]
                        merged_options = default_options + formats_list
                        self.format_combo["values"] = merged_options
                        self.format_var.set(formats_list[0])
                        self.status_label.config(text="Formats analyzed successfully")
                    else:
                        self.status_label.config(text="No custom formats returned. Used fallback options.")
                    self.probe_btn.config(state="normal")
                
                elif msg_type == "done":
                    self.download_btn.config(state="normal")
                    self.probe_btn.config(state="normal")
                    self.btnCancel.config(state="disabled")
                    self.progress_bar["value"] = 100
                    self.status_label.config(text="Download completed successfully")
                    messagebox.showinfo("Done", "Target media downloaded successfully!")
                
                elif msg_type == "error":
                    self.download_btn.config(state="normal")
                    self.probe_btn.config(state="normal")
                    self.btnCancel.config(state="disabled")
                    self.status_label.config(text="Operation failed")
                    messagebox.showerror("Process Error", msg.get("data"))
                
                self.queue.task_done()
        except queue.Empty:
            pass
        
        self.root.after(100, self._poll_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = YtGuiApp(root)
    root.mainloop()
