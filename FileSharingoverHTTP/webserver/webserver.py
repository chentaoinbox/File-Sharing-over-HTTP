# utf-8
# author: chentao
# time:2025.10.04
# description: webserver
# language: python
# version: 1.1.2

import os
import sys
import json
import shutil
import zipfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, unquote
import cgi
import socket
import time

# 全局日志变量，供外部查看
webserver_log = []
# 全局已见客户端IP及最后访问时间映射
client_last_seen = {}
# 已登录用户映射：ip -> last_login_timestamp
logged_in_ips = {}
# 登录保持时长（秒），10分钟
AUTH_TTL = 10 * 60

def refresh_all(on_finish=None):
    """
    无中断刷新所有可刷新项（IP、端口、二维码等），只更新配置和相关类属性，不重启服务。
    刷新完成后可调用on_finish回调（如有）。
    """
    cfg = load_config()
    FileServer.SHARE_DIR = cfg['dir']
    FileServer.PASSWORD = cfg['password']
    FileServer.ENABLE_LOGIN = (cfg['pw_enabled'] == '1')
    # 重新载入配置时，需清空登录数据（按要求），但保留 webserver_log
    try:
        if logged_in_ips:
            log_message(f"重新载入配置: 清空已登录用户记录: {list(logged_in_ips.keys())}")
        logged_in_ips.clear()
        client_last_seen.clear()
    except Exception as e:
        log_message(f"重新载入配置: 清空已登录用户记录异常: {e}")
    # 端口刷新仅在端口未变时有效，否则需重启服务
    try:
        port_new = int(cfg['port']) if cfg['port'].isdigit() else 8000
        if port_new == FileServer.PORT:
            FileServer.PORT = port_new
            # 刷新完成后通知外部
            if on_finish:
                on_finish()
        else:
            # 端口变化需重启服务，兼容原逻辑
            force_stop_server()
            time.sleep(0.5)
            start_server()
            if on_finish:
                on_finish()
    except Exception:
        if on_finish:
            on_finish()

def log_message(msg):
    """追加日志到全局变量，并可扩展为写文件等。格式：时间+信息"""
    now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    webserver_log.append(f"{now} {msg}")

def get_log():
    """
    获取当前日志内容（列表，每行为字符串）。
    :return: list[str]
    """
    return list(webserver_log)

def get_config_dir():
    # 支持PyInstaller打包后路径
    if hasattr(sys, '_MEIPASS'):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.join(base_dir,'../')
    #print(base_dir)
    return os.path.join(base_dir, 'config')

def get_config_file():
    return os.path.join(get_config_dir(), 'config.txt')

def load_config():
    config_path = get_config_file()
    result = {'dir':'', 'port':'8000', 'pw_enabled':'1', 'password':'123456'}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    result[k] = v
    except Exception:
        pass
    #print(result)
    return result

class FileServer(SimpleHTTPRequestHandler):
    # 常用配置区
    BASE_DIR = os.path.join(os.path.dirname(__file__))  # 静态HTML目录
    SHARE_DIR = ""  # 共享目录常量，需手动指定 例如 "E:/VScode/python/wab/share"
    PORT = 8000     # 端口常量
    PASSWORD = ""
    ENABLE_LOGIN = None  # true为启用登录，false为禁用登录
    port_socket = None   # 只允许开启一个端口

    @staticmethod
    def check_port_available(port):
        """检查端口是否可用，返回True为可用，False为被占用"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('0.0.0.0', port))
            sock.close()
            return True
        except OSError:
            return False

    @classmethod
    def get_share_path(cls):
        # 自动从配置文件读取共享目录
        if not cls.SHARE_DIR:
            cfg = load_config()
            cls.SHARE_DIR = cfg.get('dir', '')
        if not cls.SHARE_DIR:
            log_message("错误：共享目录未指定，请设置 FileServer.SHARE_DIR 类属性。")
            sys.exit(1)
        return os.path.abspath(cls.SHARE_DIR)

    @classmethod
    def get_base_dir(cls):
        return cls.BASE_DIR

    def do_GET(self):
        path = urlparse(self.path).path
        query = urlparse(self.path).query
        # 新增图片目录处理
        if path.startswith('/image/'):
            img_name = unquote(path[len('/image/'):])
            img_path = os.path.join(os.path.dirname(__file__), '../image', img_name)
            if os.path.isfile(img_path):
                self.send_response(200)
                self.send_header('Content-Type', self.guess_type(img_path))
                self.send_header('Content-Length', os.path.getsize(img_path))
                self.end_headers()
                with open(img_path, 'rb') as f:
                    shutil.copyfileobj(f, self.wfile)
                return
        if path == '/list':
            self.handle_list()
        elif path == '/clients':
            self.handle_clients()
        elif path == '/config':
            self.handle_config()
        elif path.startswith('/port/'):
            action = path.split('/')[-1]
            self.handle_port_action(action)
        elif path.endswith('.zip'):
            self.handle_zip_download(path)
        else:
            # 优先尝试共享目录文件下载，支持中文路径
            rel_path = unquote(path.lstrip('/'))
            abs_path = self.safe_path(rel_path)
            if abs_path and os.path.isfile(abs_path):
                self.send_response(200)
                self.send_header('Content-Type', self.guess_type(abs_path))
                self.send_header('Content-Length', os.path.getsize(abs_path))
                self.end_headers()
                with open(abs_path, 'rb') as f:
                    shutil.copyfileobj(f, self.wfile)
            else:
                self.serve_static()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/upload':
            self.handle_upload()
        elif path == '/newfolder':
            self.handle_newfolder()
        elif path == '/login':
            self.handle_login()
        else:
            self.send_error(404)
    def handle_login(self):
        # 支持以下逻辑：
        # - 如果登录未启用（ENABLE_LOGIN False），始终返回 success=True（无需记录）
        # - 如果该IP已在 logged_in_ips 且未过期（10分钟内），直接视为已认证
        # - 否则按提交的 password 字段验证，验证成功则记录该IP的登录时间
        client_ip = self.client_address[0]
        length = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(length)
        try:
            obj = json.loads(data.decode('utf-8'))
            password = obj.get('password', '')
        except Exception:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': 'Invalid request'}, ensure_ascii=False).encode('utf-8'))
            return

        # 如果登录被禁用
        if not self.ENABLE_LOGIN:
            log_message(f"登录禁用，{client_ip} 无需密码直接访问")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}, ensure_ascii=False).encode('utf-8'))
            return

        # 清理过期登录记录
        now = time.time()
        expired = [ip for ip, ts in logged_in_ips.items() if now - ts > AUTH_TTL]
        for ip in expired:
            try:
                del logged_in_ips[ip]
            except KeyError:
                pass

        # 如果客户端已在登录列表且未过期，直接认证成功
        if client_ip in logged_in_ips:
            log_message(f"免登录验证通过: {client_ip}（{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(logged_in_ips[client_ip]))}）")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}, ensure_ascii=False).encode('utf-8'))
            return

        # 否则按密码验证
        success = (password == self.PASSWORD)
        if success:
            logged_in_ips[client_ip] = now
            log_message(f"登录成功: {client_ip} at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}")
        else:
            log_message(f"登录失败: {client_ip} (尝试密码: {password})")

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'success': success}, ensure_ascii=False).encode('utf-8'))

    def do_DELETE(self):
        # 支持删除子目录下文件/文件夹
        rel_path = unquote(self.path.lstrip('/'))
        abs_path = self.safe_path(rel_path)
        if abs_path is None:
            return
        if os.path.isfile(abs_path):
            os.remove(abs_path)
            self.send_response(204)
            self.end_headers()
        elif os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404)

    def serve_static(self):
        rel_path = urlparse(self.path).path.lstrip('/')
        abs_path = os.path.join(self.get_base_dir(), rel_path)
        if rel_path == '' or rel_path == 'webserver.html':
            abs_path = os.path.join(self.get_base_dir(), 'webserver.html')
        if os.path.isfile(abs_path):
            self.send_response(200)
            self.send_header('Content-Type', self.guess_type(abs_path))
            self.send_header('Content-Length', os.path.getsize(abs_path))
            self.end_headers()
            with open(abs_path, 'rb') as f:
                shutil.copyfileobj(f, self.wfile)
        else:
            self.send_error(404)

    def handle_list(self):
        # 支持访问子目录，默认根目录
        query = urlparse(self.path).query
        params = dict([kv.split('=') for kv in query.split('&') if '=' in kv])
        rel_dir = params.get('dir', '').strip()
        abs_dir = self.safe_path(rel_dir) if rel_dir else self.get_share_path()
        if abs_dir is None or not os.path.isdir(abs_dir):
            self.send_error(404)
            return
        items = []
        for entry in os.scandir(abs_dir):
            if entry.is_dir():
                folder_size = self.get_folder_size(os.path.join(abs_dir, entry.name))
                size_str = f"{round(folder_size/1024,2)} KB" if folder_size < 1024*1024 else f"{round(folder_size/1024/1024,2)} MB"
                items.append({
                    'name': entry.name,
                    'isFolder': True,
                    'canOpen': True,
                    'size': size_str  # 文件夹大小
                })
            else:
                size = round(entry.stat().st_size / 1024, 2)
                items.append({
                    'name': entry.name,
                    'size': f"{size} KB" if size < 1024 else f"{round(size/1024,2)} MB",
                    'isFolder': False,
                    'canOpen': False
                })
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(items, ensure_ascii=False).encode('utf-8'))

    def get_folder_size(self, folder):
        total = 0
        for root, dirs, files in os.walk(folder):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total += os.path.getsize(fp)
                except Exception:
                    pass
        return total

    def handle_upload(self):
        # 支持上传到子目录，参数dir
        query = urlparse(self.path).query
        params = dict([kv.split('=') for kv in query.split('&') if '=' in kv])
        rel_dir = params.get('dir', '').strip()
        target_dir = self.safe_path(rel_dir) if rel_dir else self.get_share_path()
        if target_dir is None or not os.path.isdir(target_dir):
            self.send_error(400, "目标目录不存在")
            return
        ctype, pdict = cgi.parse_header(self.headers.get('Content-Type'))
        if ctype == 'multipart/form-data':
            pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
            pdict['CONTENT-LENGTH'] = int(self.headers.get('Content-Length'))
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD':'POST'}, keep_blank_values=True)
            fileitem = form['file']
            if fileitem.filename:
                save_path = os.path.join(target_dir, fileitem.filename)
                if not self.safe_path(os.path.relpath(save_path, self.get_share_path())):
                    self.send_error(403, "禁止越权上传")
                    return
                with open(save_path, 'wb') as f:
                    shutil.copyfileobj(fileitem.file, f)
                self.send_response(204)
                self.end_headers()
            else:
                self.send_error(400, "No file")
        else:
            self.send_error(400, "Invalid form")

    def handle_newfolder(self):
        # 支持在任意子目录新建文件夹，参数dir
        query = urlparse(self.path).query
        params = dict([kv.split('=') for kv in query.split('&') if '=' in kv])
        rel_dir = params.get('dir', '').strip()
        length = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(length)
        try:
            obj = json.loads(data.decode('utf-8'))
            name = obj.get('name', '').strip()
            if not name:
                self.send_error(400, "No name")
                return
            # 允许递归创建不存在的父目录
            if rel_dir:
                folder_path = os.path.join(self.get_share_path(), rel_dir, name)
            else:
                folder_path = os.path.join(self.get_share_path(), name)
            # 检查是否越权
            if not self.safe_path(os.path.relpath(folder_path, self.get_share_path())):
                self.send_error(403, "禁止越权新建")
                return
            os.makedirs(folder_path, exist_ok=True)
            self.send_response(204)
            self.end_headers()
        except Exception:
            self.send_error(500, "Create failed")

    def handle_zip_download(self, path):
        # 支持多级子目录打包和PDF单文件打包
        zip_path = unquote(path.lstrip('/'))
        if not zip_path.endswith('.zip'):
            self.send_error(404)
            return
        folder_rel = zip_path[:-4]  # 去掉.zip
        abs_folder = self.safe_path(folder_rel)
        # 生成zip文件名，避免中文导致header异常
        zip_name = os.path.basename(folder_rel) + '.zip'
        # RFC 6266: 使用Content-Disposition的filename*参数支持中文
        disposition = f'attachment; filename="{zip_name.encode("utf-8").decode("latin1", "ignore")}"'
        # 如果有非ASCII字符，添加filename*参数
        if any(ord(c) > 127 for c in zip_name):
            disposition += f"; filename*=UTF-8''{self._url_quote(zip_name)}"
        # 如果是文件夹则打包整个文件夹
        if abs_folder and os.path.isdir(abs_folder):
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Disposition', disposition)
            self.end_headers()
            with zipfile.ZipFile(self.wfile, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
                for root, dirs, files in os.walk(abs_folder):
                    for file in files:
                        abs_file = os.path.join(root, file)
                        rel_file = os.path.relpath(abs_file, abs_folder)
                        with open(abs_file, 'rb') as f:
                            zf.writestr(rel_file, f.read())
            return
        # 如果是PDF文件则只打包该文件
        if abs_folder and os.path.isfile(abs_folder) and abs_folder.lower().endswith('.pdf'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Disposition', disposition)
            self.end_headers()
            with zipfile.ZipFile(self.wfile, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
                with open(abs_folder, 'rb') as f:
                    zf.writestr(os.path.basename(abs_folder), f.read())
            return
        # 其它情况404
        self.send_error(404)

    def _url_quote(self, s):
        # RFC 5987编码，供filename*使用
        from urllib.parse import quote
        return quote(s.encode('utf-8'))


    def handle_config(self):
        # 返回是否需要登录，由本地配置决定
        # 同时返回当前请求IP是否已认证（在登录保持期内）
        client_ip = self.client_address[0]
        # 清理过期登录记录
        now = time.time()
        expired = [ip for ip, ts in logged_in_ips.items() if now - ts > AUTH_TTL]
        for ip in expired:
            try:
                del logged_in_ips[ip]
            except KeyError:
                pass

        authenticated = client_ip in logged_in_ips
        config = {
            "enableLogin": bool(self.ENABLE_LOGIN),
            "authenticated": bool(authenticated)
        }
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(config, ensure_ascii=False).encode('utf-8'))

    @staticmethod
    def check_port_available(port):
        """检查端口是否可用，返回True为可用，False为被占用"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('0.0.0.0', port))
            sock.close()
            return True
        except OSError:
            return False

    def check_port(self, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            s.close()
            return result != 0
        except Exception:
            return False

    def handle_port_action(self, action):
        port = self.PORT
        if action == 'check':
            # 检查端口并自动开启（如果没开）
            if FileServer.port_socket is None:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.bind(('0.0.0.0', port))
                    s.listen(1)
                    FileServer.port_socket = s
                except Exception as e:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'port': port, 'available': False, 'error': str(e)}, ensure_ascii=False).encode('utf-8'))
                    return
            result = self.check_port(port)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'port': port, 'available': result}, ensure_ascii=False).encode('utf-8'))
        elif action == 'open':
            if FileServer.port_socket is not None:
                self.send_error(400, "Port already opened")
                return
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(('0.0.0.0', port))
                s.listen(1)
                FileServer.port_socket = s
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'port': port, 'opened': True}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'port': port, 'opened': False, 'error': str(e)}, ensure_ascii=False).encode('utf-8'))
        elif action == 'close':
            if FileServer.port_socket is not None:
                FileServer.port_socket.close()
                FileServer.port_socket = None
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'closed': True}, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'closed': False, 'error': 'No port opened'}, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_error(404)

    def translate_path(self, path):
        rel_path = urlparse(path).path.lstrip('/')
        abs_path = os.path.join(self.get_base_dir(), rel_path)
        return abs_path

    def safe_path(self, rel_path):
        # 只允许访问SHARE_DIR及其子目录，rel_path，防止中文或特殊字符导致路径不一致
        rel_path_decoded = unquote(rel_path)
        abs_path = os.path.abspath(os.path.join(self.get_share_path(), rel_path_decoded))
        share_root = os.path.abspath(self.get_share_path())
        #print(f"safe_path: abs_path={abs_path}, share_root={share_root}")
        if not abs_path.startswith(share_root):
            self.send_error(403, "禁止访问目录之外的路径")
            return None
        return abs_path

    def log_message(self, format, *args):
        # 重写父类方法，将所有http访问日志归入webserver_log
        # 对请求路径进行解码，保证日志内容可读
        # 仅对字符串或bytes类型做unquote解码，保留数字等原类型以匹配format中的占位符（如 %d）
        decoded_args_list = []
        for a in args:
            try:
                if isinstance(a, bytes):
                    s = a.decode('utf-8', errors='ignore')
                    decoded_args_list.append(unquote(s))
                elif isinstance(a, str):
                    decoded_args_list.append(unquote(a))
                else:
                    decoded_args_list.append(a)
            except Exception:
                decoded_args_list.append(a)
        decoded_args = tuple(decoded_args_list)
        try:
            formatted = format % decoded_args
        except Exception:
            # 回退到简单字符串拼接，避免日志崩溃
            try:
                formatted = format % tuple(str(x) for x in decoded_args)
            except Exception:
                formatted = str(format)

        msg = "%s [%s] %s" % (
            self.client_address[0],
            self.log_date_time_string(),
            formatted
        )
        # 更新全局最后访问时间（ISO格式）
        try:
            client_last_seen[self.client_address[0]] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        except Exception:
            pass
        log_message(msg)

    def handle_clients(self):
        """
        返回已见客户端IP及最后访问时间的JSON数组，格式: [{"ip":"192.168.x.x","lastSeen":"YYYY-MM-DD HH:MM:SS"}, ...]
        """
        try:
            items = []
            for ip, ts in client_last_seen.items():
                items.append({'ip': ip, 'lastSeen': ts})
            # 按最后访问时间降序
            items.sort(key=lambda x: x.get('lastSeen', ''), reverse=True)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(items, ensure_ascii=False).encode('utf-8'))
        except Exception:
            self.send_error(500, 'Internal Server Error')


import threading
_server_thread = None
_httpd = None

def start_server():
    """
    启动WebServer服务（非阻塞，自动读取配置文件，适合外部调用）。
    """
    global _server_thread, _httpd
    cfg = load_config()
    FileServer.SHARE_DIR = cfg['dir']
    FileServer.PORT = int(cfg['port']) if cfg['port'].isdigit() else 8000
    FileServer.PASSWORD = cfg['password']
    FileServer.ENABLE_LOGIN = (cfg['pw_enabled'] == '1')
    
    def run():
        global _httpd
        os.chdir(FileServer.get_base_dir())
        # 检查端口是否被占用
        if not FileServer.check_port_available(FileServer.PORT):
            log_message(f"端口 {FileServer.PORT} 已被占用，服务启动失败。")
            return
        # 显示服务地址
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = '127.0.0.1'
        log_message(f"本机访问: http://localhost:{FileServer.PORT}")
        log_message(f"局域网访问: http://{local_ip}:{FileServer.PORT}")
        log_message(f"服务目录: {FileServer.get_share_path()}")
        try:
            _httpd = HTTPServer(('0.0.0.0', FileServer.PORT), FileServer)
            _httpd.serve_forever()
        except Exception as e:
            log_message(f"服务异常终止: {e}")
        finally:
            if _httpd is not None:
                _httpd.server_close()
                _httpd = None
    _server_thread = threading.Thread(target=run, daemon=True)
    _server_thread.start()

def force_stop_server():
    """
    外部调用强制终止WebServer服务（关闭端口，不退出调用者进程）。
    """
    global _httpd, _server_thread
    # 关闭HTTP服务
    if _httpd is not None:
        try:
            _httpd.shutdown()
        except Exception as e:
            log_message(f"HTTPD shutdown异常: {e}")
        try:
            _httpd.server_close()
        except Exception as e:
            log_message(f"HTTPD close异常: {e}")
        _httpd = None
    # 关闭端口socket
    if FileServer.port_socket is not None:
        try:
            FileServer.port_socket.close()
        except Exception as e:
            log_message(f"端口socket关闭异常: {e}")
        FileServer.port_socket = None
    # 清理登录和客户端记录（停止服务时清空）
    try:
        if logged_in_ips:
            log_message(f"清空已登录用户记录: {list(logged_in_ips.keys())}")
        logged_in_ips.clear()
    except Exception as e:
        log_message(f"清空已登录用户记录异常: {e}")
    try:
        if client_last_seen:
            log_message(f"清空已见客户端记录: {list(client_last_seen.keys())}")
        client_last_seen.clear()
    except Exception as e:
        log_message(f"清空已见客户端记录异常: {e}")
    # 关闭线程对象引用
    if _server_thread is not None:
        _server_thread = None

if __name__ == '__main__':
    import time
    import msvcrt
    print("按 S 启动服务，按 C 停止服务，Ctrl+C 退出。")
    running = False
    try:
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
                if key == 's':
                    if not running:
                        start_server()
                        print("WebServer已启动。")
                        running = True
                    else:
                        print("服务已在运行。")
                elif key == 'c':
                    if running:
                        force_stop_server()
                        print("WebServer已停止。")
                        running = False
                    else:
                        print("服务未运行。")
            time.sleep(0.1)
            if running and _httpd is None:
                print("服务已被外部终止，自动退出主进程。"); break
    except KeyboardInterrupt:
        print("\n服务已中断，安全退出。")
        force_stop_server()

# pyinstaller --onefile --icon="E:\VScode\python\wab\log.ico" --add-data "E:\VScode\python\wab\webserve\server.html;." --add-data "E:\VScode\python\wab\webserve\log.png;." E:\VScode\python\wab\webserve\serve.py

# 导出接口说明:
# - 变量: webserver_log
# - 函数: get_log()
