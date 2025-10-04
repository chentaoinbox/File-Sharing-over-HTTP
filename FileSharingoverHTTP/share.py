# utf-8
# author: chentao
# time:2025.10.04
# description: main control
# language: python
# version: 1.1
from webserver import webserver
from guiserver import guiserver
from webserver.webserver import webserver_log
from guiserver.guiserver import gui_activity_log
import threading
import tkinter as tk
import os
import datetime
import time

global gui_started
gui_started = False

# 新增：全局app对象
global_app = None

def threading_webserver():
    global gui_started
    started = False
    import time
    while True:
        if gui_started and not started:
            print("WebServer线程已启动。")
            webserver.start_server()
            started = True
        elif not gui_started and started:
            print("WebServer线程已停止。")
            webserver.force_stop_server()
            started = False
        time.sleep(0.5)

def threading_guiserver():
    global gui_started, global_app
    root = tk.Tk()
    app = guiserver.MainApp(root)
    global_app = app  # 保存全局app对象

    def sync_status():
        global gui_started
        gui_started = bool(getattr(app, 'is_started', False))
        root.after(500, sync_status)
    sync_status()

    # 刷新配置信号处理
    def on_refresh_config(input_text):
        # 实际刷新配置逻辑
        try:
            # 调用webserver无中断刷新
            from webserver.webserver import refresh_all
            def gui_notify():
                app.set_refresh_status(f"刷新成功: {input_text}")
            refresh_all(on_finish=gui_notify)
        except Exception as e:
            app.set_refresh_status(f"刷新失败: {e}")

    app.on_refresh_config_callback = on_refresh_config
    root.mainloop()

def get_log_dir():
    # 支持PyInstaller打包后路径
    import sys
    if hasattr(sys, '_MEIPASS'):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "log")

log_dir = get_log_dir()
# 若不存在则自建
if not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)
log_filename = f"log{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
log_path = os.path.join(log_dir, log_filename)

# 日志写入整合：同一秒内的日志合并为一行，格式为 [时间] 日志1 | 日志2 | ...
log_buffer = {}
log_buffer_lock = threading.Lock()

# 日志写入：每行只写一个操作
def flush_log_buffer():
    """定时将缓冲区日志写入文件，每行一个操作"""
    while True:
        time.sleep(1)
        now = int(time.time())
        to_flush = []
        with log_buffer_lock:
            for ts in list(log_buffer.keys()):
                if ts < now:
                    to_flush.append(ts)
            for ts in to_flush:
                logs = log_buffer.pop(ts)
                log_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        for log in logs:
                            line = f"[{log_time}] {log}"
                            f.write(line + "\n")
                except Exception:
                    pass

def write_log_to_file(log_line):
    ts = int(time.time())
    with log_buffer_lock:
        if ts not in log_buffer:
            log_buffer[ts] = []
        log_buffer[ts].append(log_line)

def print_logs():
    import time
    last_web_len = 0
    last_gui_len = 0
    while True:
        # 打印webserver_log新增内容
        if len(webserver_log) > last_web_len:
            for line in webserver_log[last_web_len:]:
                log_line = "[WebServer] " + line
                if global_app:
                    global_app.show_log(log_line)
                print(log_line)
                write_log_to_file(log_line)
            last_web_len = len(webserver_log)
        # 打印gui_activity_log新增内容
        if len(gui_activity_log) > last_gui_len:
            for line in gui_activity_log[last_gui_len:]:
                log_line = "[GUI] " + line
                if global_app:
                    global_app.show_log(log_line)
                # print("[GUI]", line)
                write_log_to_file(log_line)
            last_gui_len = len(gui_activity_log)
        time.sleep(1)

def sharemain():
    # 先启动GUI线程
    th_gui = threading.Thread(target=threading_guiserver, daemon=True)
    th_gui.start()
    # 启动webserver线程（自动根据gui_started控制启停）
    th_web = threading.Thread(target=threading_webserver, daemon=True)
    th_web.start()
    # 启动日志打印线程
    th_log = threading.Thread(target=print_logs, daemon=True)
    th_log.start()
    # 启动日志缓冲写入线程
    th_flush = threading.Thread(target=flush_log_buffer, daemon=True)
    th_flush.start()
    th_gui.join()

if __name__ == '__main__':
    sharemain()

    # pyinstaller --onefile --noconsole --clean --name="FileSharingoverHTTP" --icon=image\log.ico --add-data "image\change.png;image" --add-data "image\log.ico;image" --add-data "image\log.png;image" --add-data "webserver\webserver.html;webserver" share.py