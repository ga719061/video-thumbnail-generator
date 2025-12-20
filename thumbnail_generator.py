"""
影片縮圖產生器 - Video Thumbnail Generator
使用 tkinter GUI 和 cv2 處理影片截圖
支援 Synology Video Station @eaDir 縮圖格式（透過 SSH/SFTP）
"""

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import threading
from datetime import datetime

# SSH/SFTP 支援
try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

# 支援的影片格式
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpeg', '.mpg', '.3gp'}

# 輸出模式
OUTPUT_MODES = {
    'same_folder': '與影片同目錄（同名.jpg）',
    'synology_ssh': 'Synology Video Station（SSH）'
}

# 顏色主題
COLORS = {
    'bg': '#1a1a2e',
    'card': '#16213e',
    'accent': '#e94560',
    'accent_hover': '#ff6b6b',
    'text': '#eaeaea',
    'text_dim': '#a0a0a0',
    'success': '#00d9a5',
    'warning': '#ffa502',
    'error': '#ff4757',
    'listbox_bg': '#0f3460',
    'listbox_select': '#e94560',
    'log_bg': '#0a0a15',
}


class ThumbnailGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 影片縮圖產生器")
        self.root.geometry("750x1000")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS['bg'])
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 確定程式執行的路徑（相容 PyInstaller 打包）
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
            self.res_dir = getattr(sys, '_MEIPASS', self.base_dir)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            self.res_dir = self.base_dir
            
        # 設定視窗圖示
        ico_path = os.path.join(self.res_dir, "app_icon.ico")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except:
                pass
                
        self.selected_folders = []
        self.video_files = []
        self.output_mode = tk.StringVar(value='same_folder')
        
        # SSH 設定（簡化版）
        self.ssh_host = tk.StringVar()
        self.ssh_port = tk.StringVar(value='22')
        self.ssh_user = tk.StringVar()
        self.ssh_password = tk.StringVar()
        self.share_folder_name = tk.StringVar()  # 共享資料夾名稱，例如 "video" 或 "God"
        self.drive_letter = tk.StringVar()        # 磁碟機代號，例如 "Y"
        self.volume_number = tk.StringVar(value='1')  # 儲存空間編號
        
        # 縮圖設定
        self.capture_time = tk.StringVar(value='')  # 空值 = 使用中間幀
        self.overwrite_mode = tk.BooleanVar(value=False)  # 覆蓋模式
        
        # 處理記錄（避免重複跳過檢查）
        self.history_file = os.path.join(self.base_dir, 'processed_videos.json')
        self.processed_videos = self._load_history()
        
        # 設定檔
        self.settings_file = os.path.join(self.base_dir, 'settings.json')
        
        # 控制狀態
        self.is_processing = False
        self.is_paused = False
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.stop_flag = False
        
        self.sftp_client = None
        self.ssh_client = None
        
        self._setup_styles()
        self._setup_ui()
        self._load_settings()  # 載入上次的設定
    
    def _load_history(self):
        """載入已處理影片記錄"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
        except:
            pass
        return set()
    
    def _save_history(self):
        """儲存已處理影片記錄"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.processed_videos), f, ensure_ascii=False)
        except Exception as e:
            self._log(f"儲存記錄失敗: {e}", 'warning')
    
    def _load_settings(self):
        """載入上次的設定"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.ssh_host.set(settings.get('ssh_host', ''))
                    self.ssh_port.set(settings.get('ssh_port', '22'))
                    self.ssh_user.set(settings.get('ssh_user', ''))
                    self.drive_letter.set(settings.get('drive_letter', ''))
                    self.share_folder_name.set(settings.get('share_folder', ''))
                    self.volume_number.set(settings.get('volume_number', '1'))
                    self.capture_time.set(settings.get('capture_time', ''))
                    # 載入選擇的資料夾
                    folders = settings.get('folders', [])
                    for folder in folders:
                        if os.path.exists(folder) and folder not in self.selected_folders:
                            self.selected_folders.append(folder)
                            display_path = folder if len(folder) < 70 else f"...{folder[-67:]}"
                            self.folder_listbox.insert(tk.END, f"  📁 {display_path}")
                    if folders:
                        self._scan_videos()
        except:
            pass
    
    def _save_settings(self):
        """儲存當前設定"""
        try:
            settings = {
                'ssh_host': self.ssh_host.get(),
                'ssh_port': self.ssh_port.get(),
                'ssh_user': self.ssh_user.get(),
                'drive_letter': self.drive_letter.get(),
                'share_folder': self.share_folder_name.get(),
                'volume_number': self.volume_number.get(),
                'capture_time': self.capture_time.get(),
                'folders': self.selected_folders
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except:
            pass
            
    def _save_settings_manual(self):
        """手動儲存按鈕點擊事件"""
        self._save_settings()
        messagebox.showinfo("成功", "設定已儲存！")
        
    def _on_closing(self):
        """當視窗關閉時自動儲存"""
        self._save_settings()
        self.root.destroy()
    
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Main.TFrame', background=COLORS['bg'])
        style.configure('Card.TFrame', background=COLORS['card'])
        
        style.configure('Title.TLabel', 
                        background=COLORS['bg'], 
                        foreground=COLORS['text'],
                        font=('Segoe UI', 18, 'bold'))
        
        style.configure('Info.TLabel',
                        background=COLORS['bg'],
                        foreground=COLORS['text_dim'],
                        font=('Segoe UI', 10))
        
        style.configure('Status.TLabel',
                        background=COLORS['bg'],
                        foreground=COLORS['success'],
                        font=('Segoe UI', 10, 'bold'))
        
        style.configure('Action.TButton',
                        background=COLORS['accent'],
                        foreground='white',
                        font=('Segoe UI', 9, 'bold'),
                        padding=(12, 6))
        style.map('Action.TButton',
                  background=[('active', COLORS['accent_hover'])])
        
        style.configure('Secondary.TButton',
                        background=COLORS['card'],
                        foreground=COLORS['text'],
                        font=('Segoe UI', 9),
                        padding=(10, 5))
        style.map('Secondary.TButton',
                  background=[('active', COLORS['listbox_bg'])])
        
        style.configure('Start.TButton',
                        background=COLORS['success'],
                        foreground='white',
                        font=('Segoe UI', 11, 'bold'),
                        padding=(20, 10))
        style.map('Start.TButton',
                  background=[('active', '#00b894')])
        
        style.configure('Pause.TButton',
                        background=COLORS['warning'],
                        foreground='white',
                        font=('Segoe UI', 10, 'bold'),
                        padding=(15, 8))
        
        style.configure('Stop.TButton',
                        background=COLORS['error'],
                        foreground='white',
                        font=('Segoe UI', 10, 'bold'),
                        padding=(15, 8))
        
        style.configure('Custom.Horizontal.TProgressbar',
                        background=COLORS['accent'],
                        troughcolor=COLORS['card'],
                        thickness=18,
                        borderwidth=0)
        # 確保在 clam 主題下能看到進度條
        style.layout('Custom.Horizontal.TProgressbar', 
                     [('Horizontal.Progressbar.trough',
                       {'children': [('Horizontal.Progressbar.pbar',
                                      {'side': 'left', 'sticky': 'ns'})],
                        'sticky': 'nswe'})])
        
        style.configure('Mode.TRadiobutton',
                        background=COLORS['bg'],
                        foreground=COLORS['text'],
                        font=('Segoe UI', 9))
    
    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, style='Main.TFrame', padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題區
        title_label = ttk.Label(main_frame, text="🎬 影片縮圖產生器", style='Title.TLabel')
        title_label.pack(pady=(0, 10))
        
        # 輸出模式選擇區
        mode_frame = ttk.Frame(main_frame, style='Main.TFrame')
        mode_frame.pack(fill=tk.X, pady=(0, 8))
        
        mode_label = ttk.Label(mode_frame, text="📤 輸出模式：", style='Info.TLabel')
        mode_label.pack(side=tk.LEFT)
        
        for mode_key, mode_text in OUTPUT_MODES.items():
            rb = ttk.Radiobutton(
                mode_frame, 
                text=mode_text,
                variable=self.output_mode,
                value=mode_key,
                style='Mode.TRadiobutton',
                command=self._on_mode_change
            )
            rb.pack(side=tk.LEFT, padx=(10, 0))
        
        # 縮圖設定區
        settings_frame = ttk.Frame(main_frame, style='Main.TFrame')
        settings_frame.pack(fill=tk.X, pady=(0, 8))
        
        # 截取時間
        tk.Label(settings_frame, text="⏱️ 截取時間：", bg=COLORS['bg'], fg=COLORS['text_dim'], font=('Segoe UI', 10)).pack(side=tk.LEFT)
        tk.Entry(settings_frame, textvariable=self.capture_time, width=5, bg=COLORS['listbox_bg'], fg=COLORS['text'], 
                 insertbackground=COLORS['text'], font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(5,0))
        tk.Label(settings_frame, text="秒（留空=中間幀）", bg=COLORS['bg'], fg=COLORS['text_dim'], font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(5,0))
        
        # 分隔
        tk.Label(settings_frame, text=" │ ", bg=COLORS['bg'], fg=COLORS['text_dim']).pack(side=tk.LEFT, padx=(10,10))
        
        # 覆蓋模式
        tk.Checkbutton(settings_frame, text="🔄 覆蓋已存在的縮圖", variable=self.overwrite_mode,
                       bg=COLORS['bg'], fg=COLORS['text'], selectcolor=COLORS['listbox_bg'],
                       activebackground=COLORS['bg'], activeforeground=COLORS['text'],
                       font=('Segoe UI', 9)).pack(side=tk.LEFT)
        
        # SSH 設定區（簡化版 - 初始隱藏）
        self.ssh_frame = tk.Frame(main_frame, bg=COLORS['card'], padx=15, pady=12)
        
        ssh_title = tk.Label(self.ssh_frame, text="🔐 NAS SSH 連線設定", 
                             bg=COLORS['card'], fg=COLORS['text'], font=('Segoe UI', 10, 'bold'))
        ssh_title.grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 10))
        
        # 第一行：主機、端口
        tk.Label(self.ssh_frame, text="NAS IP:", bg=COLORS['card'], fg=COLORS['text_dim']).grid(row=1, column=0, sticky='e', padx=(0,5))
        tk.Entry(self.ssh_frame, textvariable=self.ssh_host, width=18, bg=COLORS['listbox_bg'], fg=COLORS['text'], insertbackground=COLORS['text']).grid(row=1, column=1, padx=(0,20))
        tk.Label(self.ssh_frame, text="端口:", bg=COLORS['card'], fg=COLORS['text_dim']).grid(row=1, column=2, sticky='e', padx=(0,5))
        tk.Entry(self.ssh_frame, textvariable=self.ssh_port, width=6, bg=COLORS['listbox_bg'], fg=COLORS['text'], insertbackground=COLORS['text']).grid(row=1, column=3)
        
        # 第二行：用戶名、密碼
        tk.Label(self.ssh_frame, text="帳號:", bg=COLORS['card'], fg=COLORS['text_dim']).grid(row=2, column=0, sticky='e', padx=(0,5), pady=(8,0))
        tk.Entry(self.ssh_frame, textvariable=self.ssh_user, width=18, bg=COLORS['listbox_bg'], fg=COLORS['text'], insertbackground=COLORS['text']).grid(row=2, column=1, padx=(0,20), pady=(8,0))
        tk.Label(self.ssh_frame, text="密碼:", bg=COLORS['card'], fg=COLORS['text_dim']).grid(row=2, column=2, sticky='e', padx=(0,5), pady=(8,0))
        tk.Entry(self.ssh_frame, textvariable=self.ssh_password, width=12, show='*', bg=COLORS['listbox_bg'], fg=COLORS['text'], insertbackground=COLORS['text']).grid(row=2, column=3, pady=(8,0))
        
        # 分隔線
        tk.Frame(self.ssh_frame, height=1, bg=COLORS['text_dim']).grid(row=3, column=0, columnspan=4, sticky='ew', pady=12)
        
        # 第三行：磁碟機對應設定（簡化版）
        tk.Label(self.ssh_frame, text="📁 路徑對應", bg=COLORS['card'], fg=COLORS['text'], font=('Segoe UI', 9, 'bold')).grid(row=4, column=0, columnspan=4, sticky='w', pady=(0,8))
        
        tk.Label(self.ssh_frame, text="磁碟機:", bg=COLORS['card'], fg=COLORS['text_dim']).grid(row=5, column=0, sticky='e', padx=(0,5))
        drive_frame = tk.Frame(self.ssh_frame, bg=COLORS['card'])
        drive_frame.grid(row=5, column=1, sticky='w')
        tk.Entry(drive_frame, textvariable=self.drive_letter, width=3, bg=COLORS['listbox_bg'], fg=COLORS['text'], insertbackground=COLORS['text']).pack(side=tk.LEFT)
        tk.Label(drive_frame, text=":", bg=COLORS['card'], fg=COLORS['text']).pack(side=tk.LEFT)
        
        tk.Label(self.ssh_frame, text="共享資料夾:", bg=COLORS['card'], fg=COLORS['text_dim']).grid(row=5, column=2, sticky='e', padx=(20,5))
        tk.Entry(self.ssh_frame, textvariable=self.share_folder_name, width=12, bg=COLORS['listbox_bg'], fg=COLORS['text'], insertbackground=COLORS['text']).grid(row=5, column=3, sticky='w')
        
        # Volume 設定
        tk.Label(self.ssh_frame, text="儲存空間:", bg=COLORS['card'], fg=COLORS['text_dim']).grid(row=6, column=0, sticky='e', padx=(0,5), pady=(8,0))
        vol_frame = tk.Frame(self.ssh_frame, bg=COLORS['card'])
        vol_frame.grid(row=6, column=1, sticky='w', pady=(8,0))
        tk.Label(vol_frame, text="volume", bg=COLORS['card'], fg=COLORS['text']).pack(side=tk.LEFT)
        tk.Entry(vol_frame, textvariable=self.volume_number, width=2, bg=COLORS['listbox_bg'], fg=COLORS['text'], insertbackground=COLORS['text']).pack(side=tk.LEFT)
        
        # 說明文字
        hint_frame = tk.Frame(self.ssh_frame, bg=COLORS['card'])
        hint_frame.grid(row=7, column=0, columnspan=4, sticky='w', pady=(12,0))
        tk.Label(hint_frame, text="💡 範例: 若 Y: 槽對應 NAS 的「God」資料夾", bg=COLORS['card'], fg=COLORS['text_dim'], font=('Segoe UI', 9)).pack(anchor='w')
        tk.Label(hint_frame, text="     → 磁碟機填 Y，共享資料夾填 God", bg=COLORS['card'], fg=COLORS['success'], font=('Segoe UI', 9)).pack(anchor='w')
        
        # 測試連線與儲存按鈕區
        ssh_btn_frame = tk.Frame(self.ssh_frame, bg=COLORS['card'])
        ssh_btn_frame.grid(row=8, column=0, columnspan=4, pady=(15,0))
        
        test_btn = tk.Button(ssh_btn_frame, text="🔍 測試連線 (列出共享資料夾)", 
                             bg=COLORS['accent'], fg='white', font=('Segoe UI', 9),
                             command=self._test_ssh_connection, cursor='hand2',
                             padx=10, pady=3)
        test_btn.pack(side=tk.LEFT, padx=5)
        
        save_settings_btn = tk.Button(ssh_btn_frame, text="💾 儲存設定", 
                                     bg=COLORS['success'], fg='white', font=('Segoe UI', 9),
                                     command=self._save_settings_manual, cursor='hand2',
                                     padx=15, pady=3)
        save_settings_btn.pack(side=tk.LEFT, padx=5)
        
        # 按鈕區
        btn_frame = ttk.Frame(main_frame, style='Main.TFrame')
        btn_frame.pack(pady=8)
        
        self.add_folder_btn = ttk.Button(btn_frame, text="➕ 新增資料夾", 
                                          style='Action.TButton', command=self._add_folder)
        self.add_folder_btn.pack(side=tk.LEFT, padx=3)
        
        self.remove_folder_btn = ttk.Button(btn_frame, text="🗑️ 移除選取", 
                                             style='Secondary.TButton', command=self._remove_folder)
        self.remove_folder_btn.pack(side=tk.LEFT, padx=3)
        
        self.clear_btn = ttk.Button(btn_frame, text="🧹 清空", 
                                     style='Secondary.TButton', command=self._clear_folders)
        self.clear_btn.pack(side=tk.LEFT, padx=3)
        
        # 資料夾清單區
        list_container = tk.Frame(main_frame, bg=COLORS['card'], padx=2, pady=2)
        list_container.pack(fill=tk.BOTH, expand=False, pady=8)
        
        list_frame = tk.Frame(list_container, bg=COLORS['card'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.folder_listbox = tk.Listbox(
            list_frame, 
            height=4,
            selectmode=tk.EXTENDED,
            bg=COLORS['listbox_bg'],
            fg=COLORS['text'],
            selectbackground=COLORS['listbox_select'],
            selectforeground='white',
            font=('Consolas', 9),
            borderwidth=0,
            highlightthickness=0,
            activestyle='none'
        )
        self.folder_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.folder_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.folder_listbox.config(yscrollcommand=scrollbar.set)
        
        # 統計區
        self.count_label = ttk.Label(main_frame, text="📂 請新增資料夾以開始", style='Info.TLabel')
        self.count_label.pack(pady=3)
        
        # 控制按鈕區
        self.control_frame = ttk.Frame(main_frame, style='Main.TFrame')
        
        self.start_btn = ttk.Button(self.control_frame, text="🚀 開始處理", 
                                     style='Start.TButton', command=self._start_processing)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_thumbnails_btn = ttk.Button(self.control_frame, text="🧹 清除縮圖", 
                                              style='Secondary.TButton', command=self._clear_thumbnails_clicked)
        
        self.pause_btn = ttk.Button(self.control_frame, text="⏸️ 暫停", 
                                     style='Pause.TButton', command=self._toggle_pause)
        
        self.stop_btn = ttk.Button(self.control_frame, text="⏹️ 停止", 
                                    style='Stop.TButton', command=self._stop_processing)
        
        # 進度區
        self.progress_frame = ttk.Frame(main_frame, style='Main.TFrame')
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, 
            variable=self.progress_var, 
            maximum=100, 
            length=680,
            style='Custom.Horizontal.TProgressbar'
        )
        self.progress_bar.pack(pady=5)
        
        self.progress_label = ttk.Label(self.progress_frame, text="", style='Status.TLabel')
        self.progress_label.pack()
        
        # 日誌區
        log_label = ttk.Label(main_frame, text="📋 任務日誌", style='Info.TLabel')
        log_label.pack(anchor=tk.W, pady=(8, 3))
        
        log_container = tk.Frame(main_frame, bg=COLORS['card'], padx=2, pady=2)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        log_inner = tk.Frame(log_container, bg=COLORS['log_bg'])
        log_inner.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(
            log_inner,
            height=8,
            bg=COLORS['log_bg'],
            fg=COLORS['text'],
            font=('Consolas', 9),
            borderwidth=0,
            highlightthickness=0,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        log_scrollbar = tk.Scrollbar(log_inner, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        self.log_text.tag_configure('info', foreground=COLORS['text'])
        self.log_text.tag_configure('success', foreground=COLORS['success'])
        self.log_text.tag_configure('warning', foreground=COLORS['warning'])
        self.log_text.tag_configure('error', foreground=COLORS['error'])
        self.log_text.tag_configure('time', foreground=COLORS['text_dim'])
        
        if not HAS_PARAMIKO:
            self._log("⚠️ 未安裝 paramiko，SSH 模式不可用。請執行: pip install paramiko", 'warning')
    
    def _on_mode_change(self):
        if self.output_mode.get() == 'synology_ssh':
            self.ssh_frame.pack(fill=tk.X, pady=8, after=self.root.winfo_children()[0].winfo_children()[1])
        else:
            self.ssh_frame.pack_forget()
    
    def _log(self, message, level='info'):
        def _append():
            self.log_text.config(state=tk.NORMAL)
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_text.insert(tk.END, f"[{timestamp}] ", 'time')
            self.log_text.insert(tk.END, f"{message}\n", level)
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(0, _append)
    
    def _add_folder(self):
        folder = filedialog.askdirectory(title="選擇包含影片的資料夾")
        if folder and folder not in self.selected_folders:
            self.selected_folders.append(folder)
            display_path = folder if len(folder) < 70 else f"...{folder[-67:]}"
            self.folder_listbox.insert(tk.END, f"  📁 {display_path}")
            self._scan_videos()
            self._log(f"新增資料夾: {folder}", 'info')
    
    def _remove_folder(self):
        selected = self.folder_listbox.curselection()
        for i in reversed(selected):
            self.folder_listbox.delete(i)
            del self.selected_folders[i]
        self._scan_videos()
    
    def _clear_folders(self):
        self.folder_listbox.delete(0, tk.END)
        self.selected_folders.clear()
        self._scan_videos()
    
    def _scan_videos(self):
        self.video_files = []
        
        for folder in self.selected_folders:
            for root, dirs, files in os.walk(folder):
                dirs[:] = [d for d in dirs if d != '@eaDir']
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in VIDEO_EXTENSIONS:
                        self.video_files.append(os.path.join(root, file))
        
        count = len(self.video_files)
        folder_count = len(self.selected_folders)
        
        if folder_count == 0:
            self.count_label.config(text="📂 請新增資料夾以開始")
            self.control_frame.pack_forget()
        elif count > 0:
            self.count_label.config(text=f"📊 {folder_count} 個資料夾 · {count} 個影片檔案")
            if not self.is_processing:
                self.control_frame.pack(pady=8)
                self.start_btn.pack(side=tk.LEFT, padx=5)
                self.clear_thumbnails_btn.pack(side=tk.LEFT, padx=5)
                self.pause_btn.pack_forget()
                self.stop_btn.pack_forget()
        else:
            self.count_label.config(text=f"⚠️ 沒有找到影片檔案")
            self.control_frame.pack_forget()
    
    def _connect_ssh(self):
        if not HAS_PARAMIKO:
            raise Exception("未安裝 paramiko 庫")
        
        host = self.ssh_host.get().strip()
        port = int(self.ssh_port.get().strip() or '22')
        user = self.ssh_user.get().strip()
        password = self.ssh_password.get()
        
        if not all([host, user, password]):
            raise Exception("請填寫完整的 SSH 連線資訊")
        
        self._log(f"正在連接 SSH: {user}@{host}:{port}", 'info')
        
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(host, port=port, username=user, password=password, timeout=10)
        
        self.sftp_client = self.ssh_client.open_sftp()
        self._log("SSH 連線成功！", 'success')
    
    def _disconnect_ssh(self):
        if self.sftp_client:
            self.sftp_client.close()
            self.sftp_client = None
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
    
    def _test_ssh_connection(self):
        """測試 SSH 連線並列出共享資料夾"""
        if not HAS_PARAMIKO:
            messagebox.showerror("錯誤", "未安裝 paramiko 庫！")
            return
        
        host = self.ssh_host.get().strip()
        port = int(self.ssh_port.get().strip() or '22')
        user = self.ssh_user.get().strip()
        password = self.ssh_password.get()
        vol = self.volume_number.get().strip() or '1'
        
        if not all([host, user, password]):
            messagebox.showerror("錯誤", "請先填寫 NAS IP、帳號和密碼！")
            return
        
        try:
            self._log(f"測試連接 SSH: {user}@{host}:{port}", 'info')
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host, port=port, username=user, password=password, timeout=10)
            
            sftp = ssh.open_sftp()
            
            # 先嘗試列出 SFTP 根目錄（普通用戶會被 chroot 到這裡）
            try:
                items = sftp.listdir('/')
                # 過濾隱藏資料夾
                folders = [item for item in items if not item.startswith('@') and not item.startswith('.')]
                folders.sort()
                
                self._log(f"✓ 連線成功！", 'success')
                self._log(f"📂 可用的共享資料夾:", 'info')
                for folder in folders:
                    self._log(f"   • {folder}", 'success')
                
                # 檢查是否看起來像 chroot 模式（有共享資料夾名稱）
                if folders and not any(f.startswith('volume') for f in folders):
                    messagebox.showinfo("連線成功", 
                                       f"找到 {len(folders)} 個共享資料夾：\n\n" + 
                                       "\n".join(f"• {f}" for f in folders[:10]) +
                                       ("\n..." if len(folders) > 10 else "") +
                                       "\n\n請在「共享資料夾」欄位填入上述名稱之一！")
                else:
                    # 可能是 admin 用戶，可以看到 volume
                    messagebox.showinfo("連線成功", 
                                       f"檢測到 admin 權限，找到以下項目：\n\n" + 
                                       "\n".join(f"• {f}" for f in folders[:10]))
                    
            except Exception as e:
                self._log(f"列出目錄失敗: {str(e)}", 'warning')
            
            sftp.close()
            ssh.close()
            
        except Exception as e:
            self._log(f"✗ 連線失敗: {str(e)}", 'error')
            messagebox.showerror("連線失敗", str(e))
    
    def _local_to_nas_path(self, local_path):
        """將本機路徑轉換為 NAS SFTP 路徑"""
        drive = self.drive_letter.get().strip().upper().rstrip(':')
        share = self.share_folder_name.get().strip()
        
        if not drive or not share:
            raise Exception("請設定磁碟機代號和共享資料夾名稱")
        
        # 標準化路徑
        local_path = os.path.normpath(local_path)
        
        # 本機掛載根目錄
        local_mount = f"{drive}:"
        
        # 檢查路徑是否在掛載範圍內
        if not local_path.upper().startswith(local_mount.upper()):
            raise Exception(f"路徑不在 {local_mount} 範圍內")
        
        # 取得相對路徑（相對於掛載點）
        relative = local_path[len(local_mount):].lstrip('\\/')
        
        # SFTP 路徑格式：直接使用共享資料夾名稱（Synology SFTP 會 chroot 到 /volume1）
        # 所以路徑是 /ShareName/relative 而不是 /volume1/ShareName/relative
        if relative:
            nas_path = f"/{share}/{relative}".replace('\\', '/')
        else:
            nas_path = f"/{share}"
        
        return nas_path
    
    def _sftp_makedirs(self, remote_path):
        """遞迴建立遠端目錄"""
        dirs = []
        while remote_path and remote_path != '/':
            try:
                self.sftp_client.stat(remote_path)
                break  # 目錄存在
            except IOError:
                dirs.append(remote_path)
                remote_path = os.path.dirname(remote_path).replace('\\', '/')
        
        for d in reversed(dirs):
            try:
                self.sftp_client.mkdir(d)
            except IOError:
                pass  # 目錄可能已存在或無權限
    
    def _start_processing(self):
        if self.output_mode.get() == 'synology_ssh':
            if not HAS_PARAMIKO:
                messagebox.showerror("錯誤", "未安裝 paramiko 庫！\n請執行: pip install paramiko")
                return
            if not all([self.ssh_host.get(), self.ssh_user.get(), self.ssh_password.get(),
                       self.drive_letter.get(), self.share_folder_name.get()]):
                messagebox.showerror("錯誤", "請填寫完整的 SSH 連線設定和路徑對應！")
                return
        
        self.is_processing = True
        self.is_paused = False
        self.stop_flag = False
        self.pause_event.set()
        
        # 進度歸零
        self.progress_var.set(0)
        self.progress_bar['value'] = 0
        
        self.add_folder_btn.config(state=tk.DISABLED)
        self.remove_folder_btn.config(state=tk.DISABLED)
        self.clear_btn.config(state=tk.DISABLED)
        
        self.start_btn.pack_forget()
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        self.pause_btn.config(text="⏸️ 暫停")
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.progress_frame.pack(pady=8)
        
        current_mode = self.output_mode.get()
        
        self._log(f"開始處理 {len(self.video_files)} 個影片", 'success')
        self._log(f"輸出模式: {OUTPUT_MODES[current_mode]}", 'info')
        
        thread = threading.Thread(target=self._process_videos, args=(current_mode,), daemon=True)
        thread.start()

    def _clear_thumbnails_clicked(self):
        if not self.selected_folders:
            messagebox.showwarning("警告", "請先新增資料夾！")
            return
            
        if not messagebox.askyesno("確認", "確定要清除選取資料夾中的所有縮圖嗎？\n這將會刪除已產生的縮圖檔案。"):
            return
            
        current_mode = self.output_mode.get()
        if current_mode == 'synology_ssh':
            try:
                self._connect_ssh()
            except Exception as e:
                messagebox.showerror("錯誤", f"SSH 連線失敗: {str(e)}")
                return
        
        self.is_processing = True
        self.stop_flag = False
        
        # 進度歸零
        self.progress_var.set(0)
        self.progress_bar['value'] = 0
        
        # UI 狀態調整
        self.add_folder_btn.config(state=tk.DISABLED)
        self.remove_folder_btn.config(state=tk.DISABLED)
        self.clear_btn.config(state=tk.DISABLED)
        self.start_btn.pack_forget()
        self.clear_thumbnails_btn.pack_forget()
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        self.progress_frame.pack(pady=8)
        
        self.log_text.delete(1.0, tk.END)
        self._log(f"🧹 開始清除縮圖...", 'warning')
        
        thread = threading.Thread(target=self._process_clear_thumbnails, args=(current_mode,), daemon=True)
        thread.start()

    def _process_clear_thumbnails(self, output_mode):
        total = len(self.video_files)
        success_count = 0
        
        for i, video_path in enumerate(self.video_files):
            if self.stop_flag: break
            
            filename = os.path.basename(video_path)
            video_dir = os.path.dirname(video_path)
            video_name = os.path.splitext(filename)[0]
            
            try:
                if output_mode == 'synology_ssh':
                    nas_video_dir = self._local_to_nas_path(video_dir)
                    eadir_path = f"{nas_video_dir}/@eaDir/{filename}"
                    
                    # 刪除影片子資料夾
                    try:
                        # 先刪除資料夾內的所有檔案
                        items = self.sftp_client.listdir(eadir_path)
                        for item in items:
                            self.sftp_client.remove(f"{eadir_path}/{item}")
                        self.sftp_client.rmdir(eadir_path)
                        success_count += 1
                        self._log(f"🗑️ 已清除: {filename}", 'info')
                    except IOError:
                        pass # 可能不存在 @eaDir 子資料夾
                else:
                    # 本機模式
                    thumbnail_path = os.path.normpath(os.path.join(video_dir, f"{video_name}.jpg"))
                    if os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
                        success_count += 1
                        self._log(f"🗑️ 已清除: {filename}", 'info')
                
                # 從歷史記錄移除
                if video_path in self.processed_videos:
                    self.processed_videos.discard(video_path)
            except Exception as e:
                self._log(f"激 清除失敗 {filename}: {str(e)}", 'error')
                
            progress = ((i + 1) / total) * 100
            self.root.after(0, self._update_progress, progress, i + 1, total)

        # 儲存清空後的歷史記錄
        self._save_history()
        
        if output_mode == 'synology_ssh':
            self._disconnect_ssh()
            
        self.root.after(0, lambda: self._on_complete_clear(success_count))

    def _on_complete_clear(self, count):
        self.is_processing = False
        self.progress_label.config(text=f"✨ 清除完成！共移除 {count} 個項目的縮圖")
        self._log(f"✨ 清除完成！共移除 {count} 個項目的縮圖", 'success')
        self._update_ui_state()
        self._scan_folders()

    def _update_ui_state(self):
        self.add_folder_btn.config(state=tk.NORMAL)
        self.remove_folder_btn.config(state=tk.NORMAL)
        self.clear_btn.config(state=tk.NORMAL)
        self.stop_btn.pack_forget()
        self.pause_btn.pack_forget()

    
    def _toggle_pause(self):
        if self.is_paused:
            self.is_paused = False
            self.pause_event.set()
            self.pause_btn.config(text="⏸️ 暫停")
            self._log("繼續處理...", 'success')
        else:
            self.is_paused = True
            self.pause_event.clear()
            self.pause_btn.config(text="▶️ 繼續")
            self._log("已暫停", 'warning')
    
    def _stop_processing(self):
        self.stop_flag = True
        self.pause_event.set()
        self._log("正在停止...", 'warning')
    
    def _process_videos(self, output_mode):
        total = len(self.video_files)
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        if output_mode == 'synology_ssh':
            try:
                self._connect_ssh()
            except Exception as e:
                self._log(f"SSH 連線失敗: {str(e)}", 'error')
                self.root.after(0, self._on_complete, 0, 0, 0, total)
                return
        
        for i, video_path in enumerate(self.video_files):
            if self.stop_flag:
                self._log(f"已停止，處理了 {i}/{total} 個", 'warning')
                break
            
            self.pause_event.wait()
            
            if self.stop_flag:
                break
            
            filename = os.path.basename(video_path)
            overwrite = self.overwrite_mode.get()
            
            try:
                # 第一個檔案時顯示設定資訊
                if i == 0:
                    if output_mode == 'synology_ssh':
                        self._log(f"📍 路徑對應: {self.drive_letter.get()}: → /{self.share_folder_name.get()}/", 'info')
                    if overwrite:
                        self._log("🔄 覆蓋模式：開啟", 'warning')
                
                # 檢查縮圖是否已存在（非覆蓋模式下）
                # 優先檢查歷史記錄（快速），再檢查實際檔案（慢）
                if not overwrite:
                    # 如果在歷史記錄中，還要再確認縮圖真的存在
                    if video_path in self.processed_videos:
                        if self._thumbnail_exists(video_path, output_mode):
                            skip_count += 1
                            self._log(f"⏭️ {filename} (已處理)", 'info')
                            continue
                        else:
                            # 縮圖不存在了，從歷史記錄移除
                            self.processed_videos.discard(video_path)
                    elif self._thumbnail_exists(video_path, output_mode):
                        skip_count += 1
                        self._log(f"⏭️ {filename} (已存在)", 'info')
                        self.processed_videos.add(video_path)
                        continue
                
                # 生成縮圖
                self._generate_thumbnail(video_path, output_mode)
                success_count += 1
                self._log(f"✓ {filename}", 'success')
                # 加入歷史記錄
                self.processed_videos.add(video_path)
            except Exception as e:
                fail_count += 1
                self._log(f"✗ {filename}: {str(e)}", 'error')
            
            progress = ((i + 1) / total) * 100
            self.root.after(0, self._update_progress, progress, i + 1, total)
        
        if output_mode == 'synology_ssh':
            self._disconnect_ssh()
            self._log("SSH 連線已關閉", 'info')
        
        # 儲存處理記錄
        self._save_history()
        self._log(f"已儲存處理記錄（共 {len(self.processed_videos)} 筆）", 'info')
        
        # 儲存設定
        self._save_settings()
        
        self.root.after(0, self._on_complete, success_count, fail_count, skip_count, total)
    
    def _thumbnail_exists(self, video_path, output_mode):
        video_dir = os.path.dirname(video_path)
        video_filename = os.path.basename(video_path)
        video_name = os.path.splitext(video_filename)[0]
        
        if output_mode == 'synology_ssh':
            if not self.sftp_client:
                return False
            try:
                nas_video_dir = self._local_to_nas_path(video_dir)
                thumbnail_path = f"{nas_video_dir}/@eaDir/{video_filename}/SYNOVIDEO_VIDEO_SCREENSHOT.jpg"
                self.sftp_client.stat(thumbnail_path)
                return True
            except:
                return False
        else:
            thumbnail_path = os.path.normpath(os.path.join(video_dir, f"{video_name}.jpg"))
            return os.path.exists(thumbnail_path)
    
    def _generate_thumbnail(self, video_path, output_mode):
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise Exception("無法開啟影片")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        # 使用設定的截取秒數（空值 = 中間幀）
        time_str = self.capture_time.get().strip()
        if time_str:
            try:
                target_sec = float(time_str)
                target_time = target_sec if duration >= target_sec else duration / 2
            except ValueError:
                target_time = duration / 2  # 無效值時用中間幀
        else:
            target_time = duration / 2  # 空值時用中間幀
        
        target_frame = int(target_time * fps)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise Exception("無法讀取幀")
        
        height, width = frame.shape[:2]
        new_width = 800
        new_height = int(height * (new_width / width))
        resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        success, encoded = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not success:
            raise Exception("圖片編碼失敗")
        
        video_dir = os.path.dirname(video_path)
        video_filename = os.path.basename(video_path)
        video_name = os.path.splitext(video_filename)[0]
        
        if output_mode == 'synology_ssh':
            nas_video_dir = self._local_to_nas_path(video_dir)
            eadir_path = f"{nas_video_dir}/@eaDir/{video_filename}"
            thumbnail_path = f"{eadir_path}/SYNOVIDEO_VIDEO_SCREENSHOT.jpg"
            
            # 建立目錄
            self._sftp_makedirs(eadir_path)
            
            # 上傳縮圖 (僅保留 Video Station 版本)
            try:
                # 嘗試先刪除避免權限衝突
                try:
                    self.sftp_client.remove(thumbnail_path)
                except:
                    pass
                    
                with self.sftp_client.file(thumbnail_path, 'wb') as f:
                    f.write(encoded.tobytes())
                    f.flush()
                
                # 驗證寫入
                stat = self.sftp_client.stat(thumbnail_path)
                if stat.st_size == 0:
                    raise Exception("檔案大小為 0")
            except Exception as e:
                raise Exception(f"SFTP 寫入失敗 [{thumbnail_path}]: {str(e)}")
        else:
            thumbnail_path = os.path.normpath(os.path.join(video_dir, f"{video_name}.jpg"))
            with open(thumbnail_path, 'wb') as f:
                f.write(encoded.tobytes())

    
    def _update_progress(self, progress, current, total):
        self.progress_var.set(progress)
        self.progress_bar['value'] = progress  # 直接設置元件值更穩定
        status = "⏸️ 已暫停" if self.is_paused else "⏳ 處理中"
        self.progress_label.config(text=f"{status}... {current}/{total} ({progress:.0f}%)")
        self.root.update_idletasks()  # 強制 UI 刷新
    
    def _on_complete(self, success_count, fail_count, skip_count, total):
        self.is_processing = False
        
        if self.stop_flag:
            self.progress_label.config(text=f"⏹️ 已停止 - 成功 {success_count}，跳過 {skip_count}，失敗 {fail_count}")
        else:
            self.progress_label.config(text=f"✅ 完成！成功 {success_count}，跳過 {skip_count}，失敗 {fail_count}")
            self._log(f"處理完成！成功: {success_count}，跳過: {skip_count}，失敗: {fail_count}", 'success')
            
            if success_count > 0 or fail_count > 0 or skip_count > 0:
                messagebox.showinfo("🎉 完成", 
                                   f"處理完成！\n\n成功：{success_count} 個\n跳過：{skip_count} 個\n失敗：{fail_count} 個")
        
        self.add_folder_btn.config(state=tk.NORMAL)
        self.remove_folder_btn.config(state=tk.NORMAL)
        self.clear_btn.config(state=tk.NORMAL)
        
        self.pause_btn.pack_forget()
        self.stop_btn.pack_forget()
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.progress_var.set(0)


def main():
    root = tk.Tk()
    
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = ThumbnailGenerator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
