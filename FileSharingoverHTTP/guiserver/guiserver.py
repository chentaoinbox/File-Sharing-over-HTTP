# utf-8
# author: chentao
# time:2025.9.1
# description: 文件管理工具
# language: python
# 执行pyinstaller --onefile --windowed --icon=e:\VScode\python\wab\log.ico --name "文件小样" e:\VScode\python\wab\web.py 进行打包处理
# version: 1.1.2

import os
import sys
import time  
import qrcode
import threading
import tkinter as tk
from PIL import ImageDraw
from PIL import Image, ImageTk
from tkinter import filedialog, ttk
import sys  # 新增

# 配置文件路径
def get_config_dir():
    # 支持PyInstaller打包后路径
    if hasattr(sys, '_MEIPASS'):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.join(base_dir,'../')
    return os.path.join(base_dir, 'config')

def get_config_file():
    return os.path.join(get_config_dir(), 'config.txt')

CONFIG_DIR = get_config_dir()
CONFIG_FILE = get_config_file()

def ensure_config_file():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write('dir=\nport=8000\npw_enabled=1\npassword=123456\n')

def save_config(dir_path, port, pw_enabled, password):
    ensure_config_file()
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        f.write(f'dir={dir_path}\nport={port}\npw_enabled={pw_enabled}\npassword={password}\n')

def load_config():
    ensure_config_file()
    result = {'dir':'', 'port':'8000', 'pw_enabled':'1', 'password':'123456'}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    result[k] = v
    except Exception:
        pass
    return result

ensure_config_file()

# 全局变量：GUI操作日志，外部可监听
gui_activity_log = []  # 每项为字符串："时间 操作"

class FileManager:
    """文件操作功能类"""
    @staticmethod
    def list_dir(path):
        try:
            return sorted(os.listdir(path))
        except Exception as e:
            return e

    @staticmethod
    def create_folder(parent, name):
        new_path = os.path.join(parent, name)
        os.makedirs(new_path)
        return new_path

    @staticmethod
    def delete_path(path):
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
        else:
            os.remove(path)

    @staticmethod
    def copy_path(src, dst, action='copy'):
        import shutil
        if os.path.isdir(src):
            if action == 'copy':
                shutil.copytree(src, dst)
            elif action == 'cut':
                shutil.move(src, dst)
        else:
            if action == 'copy':
                shutil.copy2(src, dst)
            elif action == 'cut':
                shutil.move(src, dst)

    @staticmethod
    def rename_path(old_path, new_path):
        os.rename(old_path, new_path)

    @staticmethod
    def get_file_info(path):
        ext = os.path.splitext(path)[1][1:].lower()
        try:
            size = os.path.getsize(path)
        except Exception:
            size = 0
        size_str = f'{size/1024:.1f} KB' if size < 1024*1024 else f'{size/1024/1024:.1f} MB'
        mtime_str = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(os.path.getmtime(path)))
        return ext, size_str, mtime_str

    @staticmethod
    def get_folder_size(folder):
        """递归获取文件夹内所有文件的总大小"""
        total = 0
        for root, dirs, files in os.walk(folder):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total += os.path.getsize(fp)
                except Exception:
                    pass
        return total

    # 新增：目录刷新逻辑（原refresh_list），返回文件和文件夹信息列表
    @staticmethod
    def get_dir_items(current_dir):
        try:
            items = sorted(os.listdir(current_dir))
        except Exception as e:
            return [], e
        result = []
        file_count = 0
        for item in items:
            full_path = os.path.join(current_dir, item)
            if os.path.isdir(full_path):
                # 递归统计文件夹大小
                folder_size = FileManager.get_folder_size(full_path)
                size_str = f'{folder_size/1024:.1f} KB' if folder_size < 1024*1024 else f'{folder_size/1024/1024:.1f} MB'
                result.append({'name': item, 'type': '文件夹', 'size': size_str, 'path': full_path, 'mtime': ''})
            else:
                ext, size_str, mtime_str = FileManager.get_file_info(full_path)
                result.append({'name': item, 'type': ext, 'size': size_str, 'path': full_path, 'mtime': mtime_str})
                file_count += 1
        return result, None

class MainApp:
  
    def __init__(self, master):
        
        master.title('文件共享客户端')
        master.geometry('900x620')
        master.iconbitmap('E:\Vscode\python\share\image\log.ico')

        # 读取配置文件
        cfg = load_config()

        # 启动界面相关状态
        self.power_on = False
        # 统一目录变量
        self.dir_path = tk.StringVar(value=cfg['dir'])
        self.current_dir = cfg['dir'] if cfg['dir'] else None
        self.root_dir = cfg['dir'] if cfg['dir'] else None
        self.start_port = tk.StringVar(value=cfg['port'])
        self.on_activity = None  # 记录操作日志的回调（可选，外部可赋值）

        # 绑定变量变化自动保存配置
        self.dir_path.trace_add('write', self._on_config_change)
        self.start_port.trace_add('write', self._on_config_change)

        # 如果配置文件中目录不为空，自动刷新文件管理页内容到该目录（首次启动时生效）
        if cfg['dir']:
            try:
                self.refresh_list()
            except Exception:
                pass
        
        # 界面背景色
        self.bg_color = 'white'

        # 界面字体
        self.font = '微软雅黑'

        # 主布局：左侧导航栏，右侧内容区
        self.main_frame = tk.Frame(master, bg=self.bg_color)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧导航栏
        self.nav_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        self.nav_frame.pack(side=tk.LEFT, fill=tk.Y)
        btn_font = (self.font, 15)
        btn_width = 14
        # 导航按钮高亮色
        self.nav_normal_bg = self.bg_color
        self.nav_active_bg = '#d0d0d0'
        self.btn_size = None  # 按钮尺寸，稍后根据窗口大小计算
        self.btn_start = tk.Button(self.nav_frame, text='启动', font=btn_font, width=btn_width, relief=tk.FLAT, command=self.show_start_frame, bg=self.nav_normal_bg)
        self.btn_start.pack(fill=tk.X)
        self.btn_qrcode = tk.Button(self.nav_frame, text='快捷访问', font=btn_font, width=btn_width, relief=tk.FLAT, command=self.show_qrcode_frame, bg=self.nav_normal_bg)
        self.btn_qrcode.pack(fill=tk.X)
        self.btn_file = tk.Button(self.nav_frame, text='文件管理', font=btn_font, width=btn_width, relief=tk.FLAT, command=self.show_file_frame, bg=self.nav_normal_bg)
        self.btn_file.pack(fill=tk.X)
        self.btn_config = tk.Button(self.nav_frame, text='配置', font=btn_font, width=btn_width, relief=tk.FLAT, command=self.show_config_frame, bg=self.nav_normal_bg)
        self.btn_config.pack(fill=tk.X)


        # 右侧内容区
        self.content_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 各功能界面
        self.start_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        tk.Label(self.start_frame, text='文件共享客户端', font=(self.font, 24), bg=self.bg_color).pack(pady=30)

        # 电源按钮区（始终可点）
        power_frame = tk.Frame(self.start_frame, bg=self.bg_color)
        power_frame.pack(pady=10)
        

        # 圆形按钮，图片外接圆，图片尺寸即为圆的直径
        win_w, win_h = 900, 600
        btn_size = min(win_w, win_h) // 3
        self.btn_size = btn_size

        # 加载方形图片并裁剪为圆形
        img_raw = Image.open('E:/VScode/python/share/image/change.png').resize((btn_size, btn_size))
        mask = Image.new('L', (btn_size, btn_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, btn_size, btn_size), fill=255)
        img_circle = Image.new('RGBA', (btn_size, btn_size))
        img_circle.paste(img_raw, (0, 0), mask)
        self.img_power_off = ImageTk.PhotoImage(img_circle)
        self.img_power_on = ImageTk.PhotoImage(img_circle)

        # 使用Canvas绘制圆形按钮，图片外接圆
        self.power_bg_color = 'red'
        self.power_canvas = tk.Canvas(power_frame, width=btn_size, height=btn_size, highlightthickness=0, bd=0, bg=self.bg_color)
        self.power_canvas.pack()
        self.power_canvas.create_oval(0, 0, btn_size, btn_size, outline='', fill=self.power_bg_color, tags='circle')
        self.power_canvas_img = self.power_canvas.create_image(btn_size//2, btn_size//2, image=self.img_power_off)
        self.power_canvas.tag_raise(self.power_canvas_img)
        self.power_canvas.bind("<Button-1>", self.toggle_power)

        # 状态标签
        self.power_status_label = tk.Label(power_frame, text='状态：未启动', font=(self.font, 16), fg='red', bg=self.bg_color)
        self.power_status_label.pack(pady=10)

        # 目录路径和按钮同一行显示（左侧文本+输入框，右侧按钮，整体100%宽度）
        dir_display_frame = tk.Frame(self.start_frame, bg=self.bg_color)
        dir_display_frame.pack(fill=tk.X, pady=(10,0))
        dir_display_frame.grid_columnconfigure(0, weight=0)
        dir_display_frame.grid_columnconfigure(1, weight=1)
        dir_display_frame.grid_columnconfigure(2, weight=0)
        tk.Label(dir_display_frame, text='目录:', font=(self.font, 14), bg=self.bg_color).grid(row=0, column=0, sticky='w', padx=(8,2))
        self.dir_label = tk.Label(dir_display_frame, textvariable=self.dir_path, width=32, anchor='w', font=(self.font, 12), fg='gray', bg=self.bg_color, relief='solid', bd=1, highlightbackground='#d3d3d3', highlightthickness=1)
        self.dir_label.grid(row=0, column=1, sticky='ew', padx=2)
        self.select_dir_btn = tk.Button(dir_display_frame, text='选择目录', command=self.combined_select_directory, width=14)
        self.select_dir_btn.grid(row=0, column=2, sticky='e', padx=(2,8))

        # 端口输入区（左侧文本+输入框，右侧按钮，整体100%宽度）
        port_frame = tk.Frame(self.start_frame, bg=self.bg_color)
        port_frame.pack(fill=tk.X, pady=(4,6))
        port_frame.grid_columnconfigure(0, weight=0)
        port_frame.grid_columnconfigure(1, weight=1)
        port_frame.grid_columnconfigure(2, weight=0)
        tk.Label(port_frame, text='端口:', font=(self.font, 14), bg=self.bg_color).grid(row=0, column=0, sticky='w', padx=(8,2))
        self.port_entry = tk.Entry(port_frame, textvariable=self.start_port, width=8, font=(self.font, 12), relief='solid', bd=1, highlightbackground='#d3d3d3', highlightthickness=1)
        self.port_entry.grid(row=0, column=1, sticky='ew', padx=2)
        self.port_confirmed = False
        self.port_confirm_btn = tk.Button(port_frame, text='确定', command=self.confirm_port, width=14)
        self.port_confirm_btn.grid(row=0, column=2, sticky='e', padx=(2,8))

        # 信息显示区（两行四个框）左对齐
        info_frame = tk.Frame(self.start_frame, bg=self.bg_color)
        info_frame.pack(pady=(6,2), fill=tk.X)
        self.info_vars = {
            'password_enabled': tk.StringVar(value='关闭'),
            'password': tk.StringVar(value='关闭'),
            'local_addr': tk.StringVar(value='关闭'),
            'lan_addr': tk.StringVar(value='关闭')
        }
        label_width = 12
        value_width_1 = 16
        value_width_2 = 24
        
        # 第一行
        tk.Label(info_frame, text='密码启用:', font=(self.font, 14), anchor='w', width=label_width, bg=self.bg_color).grid(row=0, column=0, padx=(2,0), pady=2, sticky='w')
        self.info_pw_enabled_label = tk.Label(info_frame, textvariable=self.info_vars['password_enabled'], width=value_width_1, anchor='w', font=(self.font, 12), bg=self.bg_color)
        self.info_pw_enabled_label.grid(row=0, column=1, padx=(2,10), pady=2, sticky='w')
        tk.Label(info_frame, text='密码:', font=(self.font, 14), anchor='w', width=label_width, bg=self.bg_color).grid(row=0, column=2, padx=(2,0), pady=2, sticky='w')
        self.info_pw_label = tk.Label(info_frame, textvariable=self.info_vars['password'], width=value_width_2, anchor='w', font=(self.font, 12), bg=self.bg_color)
        self.info_pw_label.grid(row=0, column=3, padx=(2,0), pady=2, sticky='w')
        
        # 第二行
        tk.Label(info_frame, text='本地服务地址:', font=(self.font, 14), anchor='w', width=label_width, bg=self.bg_color).grid(row=1, column=0, padx=(2,0), pady=2, sticky='w')
        self.info_local_label = tk.Label(info_frame, textvariable=self.info_vars['local_addr'], width=value_width_1, anchor='w', font=(self.font, 12), bg=self.bg_color)
        self.info_local_label.grid(row=1, column=1, padx=(2,10), pady=2, sticky='w')
        tk.Label(info_frame, text='局域网服务地址:', font=(self.font, 14), anchor='w', width=label_width, bg=self.bg_color).grid(row=1, column=2, padx=(2,0), pady=2, sticky='w')
        self.info_lan_label = tk.Label(info_frame, textvariable=self.info_vars['lan_addr'], width=value_width_2, anchor='w', font=(self.font, 12), bg=self.bg_color)
        self.info_lan_label.grid(row=1, column=3, padx=(2,0), pady=2, sticky='w')

        # 活动信息显示框（背景同启动界面）
        activity_frame = tk.Frame(self.start_frame, bg=self.bg_color)
        activity_frame.pack(pady=(6,2), fill=tk.X)
        tk.Label(activity_frame, text='活动信息:', font=(self.font, 14), anchor='w', bg=self.bg_color).pack(side=tk.LEFT, padx=2)
        self.activity_info_var = tk.StringVar(value='')
        
        # 界面背景色
        self.activity_info_label = tk.Label(activity_frame, textvariable=self.activity_info_var, width=60, anchor='w', font=(self.font, 8), bg=self.bg_color)
        self.activity_info_label.pack(side=tk.LEFT, padx=2)
        
        # 新增：日志显示区
        self.log_text = tk.Text(self.start_frame, height=10, width=90, font=(self.font, 8), state=tk.DISABLED, bg=self.bg_color)
        self.log_text.pack(padx=10, pady=(2, 8), fill=tk.X)
        self._external_log_lines = []  # 用于外部日志推送
        
        # 启动定时刷新
        self._refresh_activity_info()
        

        # 配置界面（左侧为项，右侧为按钮或文本框，整体100%宽度，grid布局）
        self.config_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        for i in range(4):
            self.config_frame.grid_columnconfigure(i, weight=1)
        tk.Label(self.config_frame, text='配置界面（可扩展）', font=(self.font, 20), bg=self.bg_color).grid(row=0, column=0, columnspan=4, pady=30, sticky='ew')

        # 刷新配置区（与密码项一致，采用grid布局）
        self.refresh_status_var = tk.StringVar(value='')
        self.on_refresh_config_callback = None  # 外部赋值
        tk.Label(self.config_frame, text='刷新配置:', font=(self.font, 14), anchor='w', bg=self.bg_color).grid(row=1, column=0, sticky='ew', padx=(20,8), pady=8)
        self.refresh_status_label = tk.Label(self.config_frame, textvariable=self.refresh_status_var, font=(self.font, 14), fg='black', bg=self.bg_color, width=18, anchor='w')
        self.refresh_status_label.grid(row=1, column=1, sticky='ew', padx=8, pady=8)
        self.refresh_btn = tk.Button(self.config_frame, text='刷新', font=(self.font, 12), command=self.on_refresh_config)
        self.refresh_btn.grid(row=1, column=2, sticky='ew', padx=8, pady=8)

        # 是否启用密码药丸开关
        self.enable_password = (cfg['pw_enabled'] == '1')
        self.password_var = tk.StringVar(value=cfg['password'])
        self.password_var.trace_add('write', self._on_config_change)
        self._last_pw_enabled = self.enable_password

        # 启用密码项
        tk.Label(self.config_frame, text='启用密码:', font=(self.font, 14), anchor='w', bg=self.bg_color).grid(row=2, column=0, sticky='ew', padx=(20,8), pady=8)
        self.pill_canvas = tk.Canvas(self.config_frame, width=60, height=28, bg=self.bg_color, highlightthickness=0)
        self.pill_canvas.grid(row=2, column=1,columnspan=2, sticky='e', padx=8, pady=8)
        self._draw_pill_switch()
        self.pill_canvas.bind("<Button-1>", self._toggle_pill_switch)

        # 密码项
        tk.Label(self.config_frame, text='密码:', font=(self.font, 14), anchor='w', bg=self.bg_color).grid(row=3, column=0, sticky='ew', padx=(20,8), pady=8)
        self.pwd_entry = tk.Entry(self.config_frame, textvariable=self.password_var, font=(self.font, 12), bg=self.bg_color)
        self.pwd_entry.grid(row=3, column=1, columnspan=2,sticky='ew', padx=8, pady=8)
        self.pwd_entry.config(state=tk.NORMAL)

        # 文件管理界面
        self.file_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        self.top_frame = tk.Frame(self.file_frame, bg=self.bg_color)
        self.top_frame.pack(fill=tk.X, padx=10, pady=10)
        self.select_btn = tk.Button(self.top_frame, text='选择目录', command=self.combined_select_directory)
        self.select_btn.pack(side=tk.LEFT)
        self.up_btn = tk.Button(self.top_frame, text='上一级', command=self.go_up)
        self.up_btn.pack(side=tk.LEFT, padx=5)
        self.up_btn.config(state=tk.DISABLED)
        self.new_folder_btn = tk.Button(self.top_frame, text='新建文件夹', command=self.create_folder)
        self.new_folder_btn.pack(side=tk.LEFT, padx=5)
        self.refresh_btn = tk.Button(self.top_frame, text='刷新', command=self.refresh_list)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        self.delete_btn = tk.Button(self.top_frame, text='删除', command=self.delete_selected)
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        self.copy_btn = tk.Button(self.top_frame, text='复制', command=self.copy_selected)
        self.copy_btn.pack(side=tk.LEFT, padx=5)
        self.cut_btn = tk.Button(self.top_frame, text='剪切', command=self.cut_selected)
        self.cut_btn.pack(side=tk.LEFT, padx=5)
        self.paste_btn = tk.Button(self.top_frame, text='粘贴', command=self.paste_selected)
        self.paste_btn.pack(side=tk.LEFT, padx=5)
        self.rename_btn = tk.Button(self.top_frame, text='重命名', command=self.rename_selected)
        self.rename_btn.pack(side=tk.LEFT, padx=5)

        # Treeview和滚动条
        tree_frame = tk.Frame(self.file_frame, bg=self.bg_color)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        columns = ('name', 'type', 'size', 'path', 'mtime')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='browse')
        self.tree.heading('name', text='名称', command=lambda: self.sort_column('name', False))
        self.tree.heading('type', text='类型', command=lambda: self.sort_column('type', False))
        self.tree.heading('size', text='大小', command=lambda: self.sort_column('size', False))
        self.tree.heading('path', text='路径', command=lambda: self.sort_column('path', False))
        self.tree.heading('mtime', text='修改时间', command=lambda: self.sort_column('mtime', False))
        
        # 调整列宽，隐藏路径列（width=0, stretch=False）
        self.tree.column('name', width=240, anchor='w')
        self.tree.column('type', width=50, anchor='center')
        self.tree.column('size', width=90, anchor='e')
        self.tree.column('path', width=0, stretch=False)  # 隐藏路径列
        self.tree.column('mtime', width=150, anchor='center') # 修改时间适中
        
        # 添加垂直滚动条
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scrollbar.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.tree.bind('<Double-1>', self.open_selected)

        # 右键菜单
        self.context_menu = tk.Menu(self.file_frame, tearoff=0)
        self.context_menu.add_command(label='刷新', command=self.refresh_list)
        self.context_menu.add_command(label='打开', command=self.open_selected)
        self.context_menu.add_command(label='复制', command=self.copy_selected)
        self.context_menu.add_command(label='剪切', command=self.cut_selected)
        self.context_menu.add_command(label='粘贴', command=self.paste_selected)
        self.context_menu.add_command(label='重命名', command=self.rename_selected)
        self.context_menu.add_command(label='删除', command=self.delete_selected)
        self.context_menu.add_command(label='打开文件位置', command=self.open_file_location)

        # 添加右键菜单的排序选项
        self.sort_menu = tk.Menu(self.context_menu, tearoff=0)
        self.sort_menu.add_command(label='按名称排序', command=lambda: self.sort_column('name', False))
        self.sort_menu.add_command(label='按类型排序', command=lambda: self.sort_column('type', False))
        self.sort_menu.add_command(label='按大小排序', command=lambda: self.sort_column('size', False))
        self.sort_menu.add_command(label='按修改时间排序', command=lambda: self.sort_column('mtime', False))
        self.context_menu.add_cascade(label='排序', menu=self.sort_menu)
        self.tree.bind('<Button-3>', self.show_context_menu)
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(self.file_frame, textvariable=self.status_var, anchor='w', fg='blue', bg=self.bg_color)
        self.status_label.pack(fill=tk.X, padx=10, pady=(0,5))
        self.rename_var = tk.StringVar()
        self.rename_entry = tk.Entry(self.file_frame, textvariable=self.rename_var, font=(self.font, 12), bg=self.bg_color)
        self.rename_entry.place_forget()
        self.rename_entry.bind('<Return>', self._input_confirm)
        self.rename_entry.bind('<Escape>', self._input_cancel)
        self._input_mode = None
        self._rename_target_path = None

        # 二维码快速访问界面
        self.qrcode_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        self.qr_title = tk.Label(self.qrcode_frame, text='快捷访问二维码', font=(self.font, 18), bg=self.bg_color)
        self.qr_title.grid(row=0, column=0, columnspan=2, pady=(30,10), sticky='nsew')
        self.qrcode_frame.grid_columnconfigure(0, weight=1)
        self.qrcode_frame.grid_columnconfigure(1, weight=1)
        self.qr_labels = []

        # 默认显示启动界面
        self.show_start_frame()

    def confirm_port(self):
        # 端口确认后只设置标志，不禁用控件
        self.port_confirmed = True
        # 保持端口输入框和按钮可用（未启动状态下）
        if not self.power_on:
            self.port_entry.config(state=tk.NORMAL)
            self.port_confirm_btn.config(state=tk.NORMAL)
        else:
            self.port_entry.config(state=tk.DISABLED)
            self.port_confirm_btn.config(state=tk.DISABLED)

    def toggle_power(self, event=None):
        self.update_qr()
        self.log_activity('点击启动/关闭')
        # 启动按钮逻辑：无目录时直接调用选择目录
        if not self.dir_path.get():
            self.log_activity('启动时未选择目录，弹出目录选择')
            dir_path = filedialog.askdirectory(title='选择要检索的目录')
            if dir_path:
                self.root_dir = dir_path
                self.current_dir = dir_path
                self.dir_path.set(dir_path)
                self.select_btn.config(state=tk.DISABLED)
                self.up_btn.config(state=tk.DISABLED)
                self.select_dir_btn.config(state=tk.DISABLED)
                self.refresh_list()
                self.dir_label.config(fg='gray', bg=self.bg_color)
            else:
                self.dir_path.set('')
                self.dir_label.config(fg='red', bg=self.bg_color)
                self.log_activity('启动时未选择目录，用户取消')
                return

        # 切换状态时同步禁用所有相关控件
        self.power_on = not self.power_on
        self.log_activity('切换启动状态为：%s' % ('已启动' if self.power_on else '未启动'))
        state = tk.DISABLED if self.power_on else tk.NORMAL
        
        # 同步更新两个页面的控件状态
        self._update_lock_controls()
        
        if self.power_on:
            self.power_bg_color = 'green'
            self.power_canvas.itemconfig('circle', fill=self.power_bg_color)
            self.power_canvas.itemconfig(self.power_canvas_img, image=self.img_power_on)
            self.power_status_label.config(text='状态：已启动', fg='green')
            self.port_entry.config(state=tk.DISABLED)
            self.port_confirm_btn.config(state=tk.DISABLED)
        else:
            self.power_bg_color = 'red'
            self.power_canvas.itemconfig('circle', fill=self.power_bg_color)
            self.power_canvas.itemconfig(self.power_canvas_img, image=self.img_power_off)
            self.power_status_label.config(text='状态：未启动', fg='red')
            self.port_entry.config(state=tk.NORMAL)
            self.port_confirm_btn.config(state=tk.NORMAL)

        # 信息框内容控制
        if self.power_on:
            self.info_vars['password_enabled'].set('开启' if self.enable_password else '关闭')
            self.info_vars['password'].set(self.password_var.get() if self.enable_password else '关闭')
            port = self.start_port.get()
            # 本地服务地址使用localhost
            self.info_vars['local_addr'].set(f'http://localhost:{port}')
            import socket
            try:
                hostname = socket.gethostname()
                lan_ip = socket.gethostbyname(hostname)
            except Exception:
                lan_ip = '未知'
            self.info_vars['lan_addr'].set(f'http://{lan_ip}:{port}')
        else:
            for k in self.info_vars:
                self.info_vars[k].set('关闭')
            self.activity_info_var.set('')  # 关闭时清空活动信息

    def start_select_directory(self):
        self.log_activity('点击选择目录')
        dir_path = filedialog.askdirectory(title='选择要检索的目录')
        if dir_path:
            self.log_activity(f'选择目录: {dir_path}')
            self.root_dir = dir_path
            self.current_dir = dir_path
            self.dir_path.set(dir_path)
            self.dir_label.config(fg='gray', bg=self.bg_color)
            self.up_btn.config(state=tk.DISABLED)
            self.select_btn.config(state=tk.DISABLED)
            self.refresh_list()
            self.status_var.set(f'已将 {dir_path} 设为最高级目录。')
        else:
            self.dir_path.set('')
            self.dir_label.config(fg='red', bg=self.bg_color)
            self.current_dir = None
            self.root_dir = None
            self.tree.delete(*self.tree.get_children())
            self.status_var.set('未选择目录')
            self.log_activity('选择目录取消')
        # 同步按钮状态
        self.select_dir_btn.config(state=tk.DISABLED if self.dir_path.get() else tk.NORMAL)
        self.reselect_dir_btn.config(state=tk.NORMAL if self.dir_path.get() else tk.DISABLED)
        self.select_btn.config(state=tk.DISABLED if self.dir_path.get() else tk.NORMAL)

    def start_reselect_directory(self):
        self.log_activity('点击重新选择目录')
        self.dir_path.set('')
        self.log_activity('清除目录')
        self.dir_label.config(fg='red', bg=self.bg_color)
        self.current_dir = None
        self.root_dir = None
        self.tree.delete(*self.tree.get_children())
        self.select_btn.config(state=tk.NORMAL)
        self.up_btn.config(state=tk.DISABLED)
        self.status_var.set('请重新选择目录。')
        # 同步按钮状态
        self.select_dir_btn.config(state=tk.NORMAL)
        self.reselect_dir_btn.config(state=tk.DISABLED)
        # 允许重新输入端口
        self.port_entry.config(state=tk.NORMAL)
        self.port_confirm_btn.config(state=tk.NORMAL)
        self.port_confirmed = False

    def show_start_frame(self):
        self.log_activity('切换到启动界面')
        self.file_frame.pack_forget()
        self.config_frame.pack_forget()
        self.qrcode_frame.pack_forget()
        self.start_frame.pack(fill=tk.BOTH, expand=True)
        self._update_lock_controls()
        self.btn_start.config(bg=self.nav_active_bg)
        self.btn_file.config(bg=self.nav_normal_bg)
        self.btn_config.config(bg=self.nav_normal_bg)
        self.btn_qrcode.config(bg=self.nav_normal_bg)

    def show_file_frame(self):
        self.log_activity('切换到文件管理界面')
        if not self.current_dir or not self.root_dir:
            dir_path = self.dir_path.get()
            if dir_path:
                self.current_dir = dir_path
                self.root_dir = dir_path
        self.start_frame.pack_forget()
        self.config_frame.pack_forget()
        self.qrcode_frame.pack_forget()
        self.file_frame.pack(fill=tk.BOTH, expand=True)
        self._update_lock_controls()
        self.btn_start.config(bg=self.nav_normal_bg)
        self.btn_file.config(bg=self.nav_active_bg)
        self.btn_config.config(bg=self.nav_normal_bg)
        self.btn_qrcode.config(bg=self.nav_normal_bg)
        self.refresh_list()

    def show_config_frame(self):
        self.log_activity('切换到配置界面')
        self.start_frame.pack_forget()
        self.file_frame.pack_forget()
        self.qrcode_frame.pack_forget()
        self.config_frame.pack(fill=tk.BOTH, expand=True)
        self._update_lock_controls()
        self.btn_start.config(bg=self.nav_normal_bg)
        self.btn_file.config(bg=self.nav_normal_bg)
        self.btn_config.config(bg=self.nav_active_bg)
        self.btn_qrcode.config(bg=self.nav_normal_bg)
    
    def show_qrcode_frame(self):
        self.log_activity('切换到二维码界面')
        self.start_frame.pack_forget()
        self.file_frame.pack_forget()
        self.config_frame.pack_forget()
        self.qrcode_frame.pack(fill=tk.BOTH, expand=True)
        self.update_qr()
        self.btn_start.config(bg=self.nav_normal_bg)
        self.btn_file.config(bg=self.nav_normal_bg)
        self.btn_config.config(bg=self.nav_normal_bg)
        self.btn_qrcode.config(bg=self.nav_active_bg)

    def _set_frame_controls_state(self, frame, state):
        # 禁用/恢复 frame 下所有控件
        for child in frame.winfo_children():
            try:
                child.config(state=state)
            except Exception:
                pass
            # 递归处理嵌套 Frame
            if isinstance(child, tk.Frame):
                self._set_frame_controls_state(child, state)

    def _update_lock_controls(self):
        # 启动页锁定项在所有页面都锁定
        if self.power_on:
            self.select_dir_btn.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
            self.port_confirm_btn.config(state=tk.DISABLED)
            self.select_btn.config(state=tk.DISABLED)
        else:
            self.select_dir_btn.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.NORMAL)
            self.port_confirm_btn.config(state=tk.NORMAL)
            self.select_btn.config(state=tk.NORMAL)

    def _draw_pill_switch(self):
        # 药丸开关绘制为圆角矩形
        self.pill_canvas.delete("all")
        bg_color = "#4caf50" if self.enable_password else "#ccc"
        knob_color = "#fff"
        # 绘制圆角矩形（药丸底座）
        r = 14  # 半径
        w, h = 60, 28
        self.pill_canvas.create_rectangle(r, 0, w - r, h, fill=bg_color, outline=bg_color)
        self.pill_canvas.create_oval(0, 0, 2*r, h, fill=bg_color, outline=bg_color)
        self.pill_canvas.create_oval(w-2*r, 0, w, h, fill=bg_color, outline=bg_color)
        # 滑块
        x = w - r - 6 if self.enable_password else 6
        self.pill_canvas.create_oval(x, 4, x+20, 24, fill=knob_color, outline=knob_color)
        # txt = "开" if self.enable_password else "关"
        # self.pill_canvas.create_text(w//2, h//2, text=txt, fill="#fff", font=(self.font, 12, 'bold'))

    def _toggle_pill_switch(self, event=None):
        # 检测密码启用变化
        old = self.enable_password
        self.log_activity('切换密码启用状态为：%s' % ('启用' if not self.enable_password else '关闭'))
        # 切换药丸开关状态
        self.enable_password = not self.enable_password
        self._draw_pill_switch()
        # 密码输入框始终可输入
        self.pwd_entry.config(state=tk.NORMAL)
        if old != self.enable_password:
            self._on_config_change()

    def _on_config_change(self, *args):
        # 统一保存配置到文件
        dir_path = self.dir_path.get()
        port = self.start_port.get()
        pw_enabled = '1' if self.enable_password else '0'
        password = self.password_var.get()
        threading.Thread(target=save_config, args=(dir_path, port, pw_enabled, password), daemon=True).start()

    def log_activity(self, action: str):
        """记录一条GUI操作，格式：时间 操作"""
        t = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        entry = f"{t} {action}"
        gui_activity_log.append(entry)
        if self.on_activity:
            self.on_activity(entry)

    def set_activity_info(self, info: str):
        """外部调用设置活动信息显示框内容（会优先显示外部日志）"""
        self._external_activity_info = info
        self.activity_info_var.set(info)

    def show_log(self, log: str):
        """外部调用：只显示最新一条日志到日志显示区，并同步到活动信息框"""
        self._external_log_lines.append(log)
        if len(self._external_log_lines) > 100:
            self._external_log_lines = self._external_log_lines[-100:]
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)  # 清空旧内容
        self.log_text.insert(tk.END, log)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.activity_info_var.set(log)

    def _refresh_activity_info(self):
        # 优先显示外部推送的日志
        if hasattr(self, '_external_log_lines') and self._external_log_lines:
            latest = self._external_log_lines[-1]
            self.activity_info_var.set(str(latest))
        else:
            try:
                ext_log = sys.modules.get(__name__).__dict__.get('gui_activity_log', None)
            except Exception:
                ext_log = None
            log_list = ext_log if ext_log is not None else []
            if hasattr(self, '_external_activity_info') and self._external_activity_info:
                self.activity_info_var.set(str(self._external_activity_info))
            else:
                latest = log_list[-1] if log_list else ''
                self.activity_info_var.set(str(latest))
        self.activity_info_label.after(500, self._refresh_activity_info)

    def refresh_current_dir(self):
        """外部调用刷新当前文件共享目录"""
        self.refresh_list()

    # 文件管理相关方法补充到 MainApp
    def select_directory(self):
        dir_path = filedialog.askdirectory(title='选择要检索的目录')
        if dir_path:
            self.root_dir = dir_path
            self.current_dir = dir_path
            self.dir_path.set(dir_path)
            self.up_btn.config(state=tk.DISABLED)
            self.select_btn.config(state=tk.DISABLED)
            self.refresh_list()
            self.status_var.set(f'已将 {dir_path} 设为最高级目录。')
        else:
            self.dir_path.set('')
            self.current_dir = None
            self.root_dir = None
            self.tree.delete(*self.tree.get_children())
            self.status_var.set('未选择目录')

    def reselect_directory(self):
        self.select_btn.config(state=tk.NORMAL)
        self.dir_path.set('')
        self.current_dir = None
        self.root_dir = None
        self.tree.delete(*self.tree.get_children())
        self.up_btn.config(state=tk.DISABLED)
        self.status_var.set('请重新选择目录。')

    def go_up(self):
        if self.current_dir and self.root_dir:
            if os.path.abspath(self.current_dir) == os.path.abspath(self.root_dir):
                self.up_btn.config(state=tk.DISABLED)
                self.status_var.set('已设为最高级目录，无法再返回上一级。')
            else:
                parent = os.path.dirname(self.current_dir)
                if os.path.abspath(parent).startswith(os.path.abspath(self.root_dir)):
                    self.current_dir = parent
                    self.dir_path.set(self.current_dir)
                    self.up_btn.config(state=tk.NORMAL if os.path.abspath(self.current_dir) != os.path.abspath(self.root_dir) else tk.DISABLED)
                    self.refresh_list()
                else:
                    self.up_btn.config(state=tk.DISABLED)
                    self.status_var.set('已设为最高级目录，无法再返回上一级。')

    def create_folder(self):
        if not self.current_dir:
            self.status_var.set('请先选择目录')
            return
        self._input_mode = 'newfolder'
        self.rename_var.set('')
        self._show_input_entry()
        self.status_var.set('请输入新建文件夹名称，Enter确定，Esc取消')

    def delete_selected(self):
        self.log_activity('点击删除')
        sel = self.tree.selection()
        if not sel:
            self.status_var.set('请先选择要删除的项')
            return
        item = self.tree.item(sel[0])
        path = item['values'][3]
        if not os.path.abspath(path).startswith(os.path.abspath(self.root_dir)):
            self.status_var.set('只能删除最高级目录及其子目录下的文件或文件夹。')
            return
        try:
            self.log_activity(f'删除: {path}')
            FileManager.delete_path(path)
            self.refresh_list()
            self.status_var.set(f'已删除: {path}')
        except Exception as e:
            self.status_var.set(f'删除失败: {e}')

    def copy_selected(self):
        self.log_activity('点击复制')
        sel = self.tree.selection()
        if not sel:
            self.status_var.set('请先选择要复制的项')
            return
        item = self.tree.item(sel[0])
        self._clipboard_path = item['values'][3]
        self.log_activity(f'复制: {self._clipboard_path}')
        self._clipboard_action = 'copy'
        self.status_var.set(f'已复制: {self._clipboard_path}')

    def cut_selected(self):
        self.log_activity('点击剪切')
        sel = self.tree.selection()
        if not sel:
            self.status_var.set('请先选择要剪切的项')
            return
        item = self.tree.item(sel[0])
        self._clipboard_path = item['values'][3]
        self.log_activity(f'剪切: {self._clipboard_path}')
        self._clipboard_action = 'cut'
        self.status_var.set(f'已剪切: {self._clipboard_path}')

    def paste_selected(self):
        self.log_activity('点击粘贴')
        if not hasattr(self, '_clipboard_path') or not self._clipboard_path:
            self.status_var.set('剪贴板为空')
            return
        if not self.current_dir:
            self.status_var.set('请先选择目标目录')
            return
        src = self._clipboard_path
        base_name = os.path.basename(src)
        dst = os.path.join(self.current_dir, base_name)
        if os.path.exists(dst):
            self.status_var.set('目标已存在同名项')
            return
        try:
            FileManager.copy_path(src, dst, self._clipboard_action)
            self.log_activity(f'粘贴: {src} 到 {dst} ({self._clipboard_action})')
            self.status_var.set(f'已粘贴到: {dst}')
            self.refresh_list()
            if self._clipboard_action == 'cut':
                self._clipboard_path = None
        except Exception as e:
            self.status_var.set(f'粘贴失败: {e}')

    def rename_selected(self):
        self.log_activity('点击重命名')
        sel = self.tree.selection()
        if not sel:
            self.status_var.set('请先选择要重命名的项')
            return
        item = self.tree.item(sel[0])
        old_path = item['values'][3]
        old_name = os.path.basename(old_path)
        self._input_mode = 'rename'
        self.log_activity(f'准备重命名: {old_path}')
        self._rename_target_path = old_path
        self.rename_var.set(old_name)
        self._show_input_entry()
        self.status_var.set('请输入新名称，Enter确定，Esc取消')

    def _show_input_entry(self):
        self.rename_entry.place_forget()
        self.file_frame.update_idletasks()
        w = self.file_frame.winfo_width()
        h = self.file_frame.winfo_height()
        entry_width = 260
        entry_height = 28
        x = w - entry_width - 20
        y = h - entry_height - 2
        self.rename_entry.place(x=x, y=y, width=entry_width, height=entry_height)
        self.rename_entry.focus_set()
        self.rename_entry.selection_range(0, tk.END)

    def _input_confirm(self, event=None):
        self.log_activity('输入确认')
        if self._input_mode == 'rename':
            new_name = self.rename_var.get().strip()
            old_path = self._rename_target_path
            if not new_name:
                self.status_var.set('未输入新名称')
                self._input_cancel()
                return
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            if os.path.exists(new_path):
                self.status_var.set('已存在同名项')
                self._input_cancel()
                return
            try:
                FileManager.rename_path(old_path, new_path)
                self.log_activity(f'重命名: {old_path} -> {new_name}')
                self.status_var.set(f'已重命名为: {new_name}')
                self.refresh_list()
            except Exception as e:
                self.status_var.set(f'重命名失败: {e}')
            self._input_cancel()
        elif self._input_mode == 'newfolder':
            folder_name = self.rename_var.get().strip()
            if not folder_name:
                self.status_var.set('未输入文件夹名称。')
                self._input_cancel()
                return
            try:
                FileManager.create_folder(self.current_dir, folder_name)
                self.log_activity(f'新建文件夹: {folder_name} 于 {self.current_dir}')
                self.refresh_list()
                self.status_var.set(f'文件夹 "{folder_name}" 创建成功。')
            except Exception as e:
                self.status_var.set(f'创建失败: {e}')
            self._input_cancel()

    def _input_cancel(self, event=None):
        self.rename_entry.place_forget()
        self._input_mode = None
        self._rename_target_path = None

    def open_selected(self, event=None):
        self.log_activity('点击打开')
        sel = self.tree.selection()
        if not sel:
            self.status_var.set('请先选择要打开的文件')
            return
        item = self.tree.item(sel[0])
        path = item['values'][3]
        if os.path.isdir(path):
            self.current_dir = path
            self.log_activity(f'打开文件夹: {path}')
            self.up_btn.config(state=tk.NORMAL if os.path.abspath(self.current_dir) != os.path.abspath(self.root_dir) else tk.DISABLED)
            self.refresh_list()
        else:
            try:
                os.startfile(path)
                self.log_activity(f'打开文件: {path}')
                self.status_var.set(f'已打开: {path}')
            except Exception as e:
                self.status_var.set(f'无法打开文件: {e}')

    def open_file_location(self):
        self.log_activity('点击打开文件位置')
        sel = self.tree.selection()
        if not sel:
            self.status_var.set('请先选择文件或文件夹')
            return
        item = self.tree.item(sel[0])
        path = item['values'][3]
        if os.path.exists(path):
            folder_path = os.path.dirname(path) if os.path.isfile(path) else os.path.dirname(os.path.abspath(path))
            try:
                os.startfile(folder_path)
                self.log_activity(f'打开文件位置: {folder_path}')
                self.status_var.set(f'已打开位置: {folder_path}')
            except Exception as e:
                self.status_var.set(f'无法打开位置: {e}')
        else:
            self.status_var.set('所选项不存在')

    def show_context_menu(self, event):
        self.log_activity('右键菜单')
        self.context_menu.post(event.x_root, event.y_root)

    def sort_column(self, col, reverse):
        self.log_activity(f'排序: {col} reverse={reverse}')
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        if col == 'size':
            def parse_size(size_str):
                if 'KB' in size_str:
                    return float(size_str.replace(' KB', '')) * 1024
                elif 'MB' in size_str:
                    return float(size_str.replace(' MB', '')) * 1024 * 1024
                elif size_str:
                    return float(size_str)
                return 0
            l.sort(key=lambda t: parse_size(t[0]), reverse=reverse)
        elif col == 'mtime':
            import time
            min_time = time.strptime('1970-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
            l.sort(key=lambda t: time.strptime(t[0], '%Y-%m-%d %H:%M:%S') if t[0] else min_time, reverse=reverse)
        else:
            l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        if not self.current_dir:
            self.status_var.set('未选择目录')
            return
        items, err = FileManager.get_dir_items(self.current_dir)
        if err:
            self.status_var.set(f'读取失败: {err}')
            return
        file_count = sum(1 for i in items if i['type'] != '文件夹')
        for item in items:
            self.tree.insert('', tk.END, values=(item['name'], item['type'], item['size'], item['path'], item['mtime']))
        self.status_var.set(f'共找到 {file_count} 个文件，{len(items)-file_count} 个文件夹')
        
    def set_refresh_status(self, status: str):
        self.refresh_status_var.set(status)
        self.config_frame.after(1000, lambda: self.refresh_status_var.set(''))

    def get_refresh_input(self):
        return None

    def on_refresh_config(self):
        # 触发外部回调
        if hasattr(self, 'on_refresh_config_callback') and self.on_refresh_config_callback:
            self.on_refresh_config_callback(self.get_refresh_input())
        # GUI自身也刷新配置
        cfg = load_config()
        self.dir_path.set(cfg['dir'])
        self.start_port.set(cfg['port'])
        self.enable_password = (cfg['pw_enabled'] == '1')
        self.password_var.set(cfg['password'])
        self._draw_pill_switch()
        # 刷新IP显示区
        if self.power_on:
            self.info_vars['password_enabled'].set('开启' if self.enable_password else '关闭')
            self.info_vars['password'].set(self.password_var.get() if self.enable_password else '关闭')
            port = self.start_port.get()
            self.info_vars['local_addr'].set(f'http://localhost:{port}')
            import socket
            try:
                hostname = socket.gethostname()
                lan_ip = socket.gethostbyname(hostname)
            except Exception:
                lan_ip = '未知'
            self.info_vars['lan_addr'].set(f'http://{lan_ip}:{port}')
        else:
            for k in self.info_vars:
                self.info_vars[k].set('关闭')
        # 刷新二维码
        self.update_qr()
        self.set_refresh_status('已刷新')

    @property
    def is_started(self):
        """外部获取是否已启动"""
        return getattr(self, 'power_on', False)
    
    def update_qr(self):
        local_url = self.info_vars['local_addr'].get()
        lan_url = self.info_vars['lan_addr'].get()
        for lbl in getattr(self, 'qr_labels', []):
            lbl.destroy()
        self.qr_labels = []
        if not self.power_on:
            return
        local_img = self.generate_qrcode(local_url)
        lan_img = self.generate_qrcode(lan_url)
        self.local_qr_img = ImageTk.PhotoImage(local_img.resize((160, 160)).convert('RGB'))
        self.lan_qr_img = ImageTk.PhotoImage(lan_img.resize((160, 160)).convert('RGB'))
        lbl1 = tk.Label(self.qrcode_frame, image=self.local_qr_img, bg=self.bg_color)
        lbl2 = tk.Label(self.qrcode_frame, image=self.lan_qr_img, bg=self.bg_color)
        lbl1.grid(row=1, column=0, padx=(60,10), pady=(0,2), sticky='n')
        lbl2.grid(row=1, column=1, padx=(10,60), pady=(0,2), sticky='n')
        lbl3 = tk.Label(self.qrcode_frame, text=local_url, font=(self.font, 12), bg=self.bg_color)
        lbl4 = tk.Label(self.qrcode_frame, text=lan_url, font=(self.font, 12), bg=self.bg_color)
        lbl3.grid(row=2, column=0, padx=(60,10), pady=(0,18), sticky='n')
        lbl4.grid(row=2, column=1, padx=(10,60), pady=(0,18), sticky='n')
        self.qr_labels.extend([lbl1, lbl2, lbl3, lbl4])

    def generate_qrcode(self, text: str) -> Image.Image:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color=self.bg_color)
        return img

    def combined_select_directory(self):
        # 先执行重选目录逻辑
        self.dir_path.set('')
        self.log_activity('点击选择目录')
        self.log_activity('清除目录')
        self.dir_label.config(fg='red', bg=self.bg_color)
        self.current_dir = None
        self.root_dir = None
        self.tree.delete(*self.tree.get_children())
        self.select_btn.config(state=tk.NORMAL)
        self.up_btn.config(state=tk.DISABLED)
        self.status_var.set('请重新选择目录。')
        # 允许重新输入端口
        self.port_entry.config(state=tk.NORMAL)
        self.port_confirm_btn.config(state=tk.NORMAL)
        self.port_confirmed = False
        # 再执行选择目录逻辑
        dir_path = filedialog.askdirectory(title='选择要检索的目录')
        if dir_path:
            self.log_activity(f'选择目录: {dir_path}')
            self.root_dir = dir_path
            self.current_dir = dir_path
            self.dir_path.set(dir_path)
            self.dir_label.config(fg='gray', bg=self.bg_color)
            self.up_btn.config(state=tk.DISABLED)
            self.select_btn.config(state=tk.DISABLED)
            self.refresh_list()
            self.status_var.set(f'已将 {dir_path} 设为最高级目录。')
        else:
            self.dir_path.set('')
            self.dir_label.config(fg='red', bg=self.bg_color)
            self.current_dir = None
            self.root_dir = None
            self.tree.delete(*self.tree.get_children())
            self.status_var.set('未选择目录')
            self.log_activity('选择目录取消')
        self._update_lock_controls()

    def _refresh_activity_info(self):
        # 优先显示外部推送的日志
        if hasattr(self, '_external_log_lines') and self._external_log_lines:
            latest = self._external_log_lines[-1]
            self.activity_info_var.set(str(latest))
        else:
            try:
                ext_log = sys.modules.get(__name__).__dict__.get('gui_activity_log', None)
            except Exception:
                ext_log = None
            log_list = ext_log if ext_log is not None else []
            if hasattr(self, '_external_activity_info') and self._external_activity_info:
                self.activity_info_var.set(str(self._external_activity_info))
            else:
                latest = log_list[-1] if log_list else ''
                self.activity_info_var.set(str(latest))
        self.activity_info_label.after(10, self._refresh_activity_info)

if __name__ == '__main__':
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()
