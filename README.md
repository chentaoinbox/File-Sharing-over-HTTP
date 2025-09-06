# File Share Tool

## Overview

This project is a cross-platform file management and sharing tool with both a graphical user interface (GUI) and a web server interface. It allows users to manage files locally and share them over the network via a browser.

## File Structure

```
FileSharingoverHTTP/
├── guiserver/
│   └── guiserver.py      # GUI application (Tkinter)
├── webserver/
│   └── webserver.py      # Web server for file sharing (HTTP)
├── image/
│   ├── change.png        # Button/icon images
│   ├── log.ico
│   └── log.png
├── config/
│   └── config.txt        # Configuration file (auto-generated)
├── share.py              # Main entry point, launches GUI and web server
├── list_all_files.py     # Utility script to list all files in the project
└── README.md             # Project documentation
```

## Main Components

- **guiserver/guiserver.py**: Provides a Tkinter-based GUI for local file management and configuration.
- **webserver/webserver.py**: Implements an HTTP server for file sharing, supporting file/folder listing, upload, download, and zip packaging.
- **share.py**: Main launcher. Starts both the GUI and web server in separate threads, and manages logging.
- **config/config.txt**: Stores user configuration such as shared directory, port, and password. Automatically created if missing.
- **image/**: Contains icons and images used by the GUI.
- **list_all_files.py**: Utility to output all file paths in the project to a text file.

## Features

- Local file management (browse, create, delete, rename, copy, cut, paste, open).
- Web-based file sharing (access via browser, upload/download, zip download).
- Password protection (optional).
- Activity and access logging.
- Configuration persistence.
- Supports both development and PyInstaller-packed (standalone executable) modes.

## Python Version

- Python 3.10 or higher is recommended.

## Required Libraries

- `tkinter` (standard library, for GUI)
- `threading` (standard library)
- `http.server`, `socket`, `shutil`, `os`, `sys`, `json`, `zipfile`, `time`, `datetime`, `cgi`, `urllib` (standard libraries)


## How to Run

1. Install required libraries.
2. Run `share.py`:
   ```bash
   python share.py
   ```
3. Use the GUI to select a shared directory and start the service.
4. Access the web interface from another device via `http://<your-ip>:<port>`.

## Packaging

To build a standalone executable (Windows example):
```bash
pyinstaller --onefile --noconsole --add-data "image\change.png;image" --add-data "image\log.ico;image" --add-data "image\log.png;image" --add-data "webserver\webserver.html;webserver" share.py
```

---

# 文件共享工具

## 概述

本项目是一个跨平台的文件管理与共享工具，包含图形界面（GUI）和网页端接口。用户可在本地管理文件，并通过浏览器在局域网内共享访问。

## 文件结构

```
File-Sharing-over-HTTP/
├── guiserver/
│   └── guiserver.py      # 图形界面应用（Tkinter）
├── webserver/
│   └── webserver.py      # 文件共享Web服务（HTTP）
├── image/
│   ├── change.png        # 按钮/图标图片
│   ├── log.ico
│   └── log.png
├── config/
│   └── config.txt        # 配置文件（自动生成）
├── share.py              # 主入口，启动GUI和Web服务
├── list_all_files.py     # 列出项目所有文件的工具脚本
└── README.md             # 项目说明文档
```

## 主要组件

- **guiserver/guiserver.py**：基于Tkinter的本地文件管理与配置界面。
- **webserver/webserver.py**：实现HTTP文件共享服务，支持文件/文件夹浏览、上传、下载、打包下载等。
- **share.py**：主启动器。分别以线程方式启动GUI和Web服务，并管理日志。
- **config/config.txt**：保存用户配置（共享目录、端口、密码等），自动生成。
- **image/**：存放界面所需的图标和图片。
- **list_all_files.py**：输出项目所有文件路径到文本文件的工具。

## 功能说明

- 本地文件管理（浏览、新建、删除、重命名、复制、剪切、粘贴、打开）。
- 网页端文件共享（浏览器访问、上传/下载、ZIP打包下载）。
- 可选密码保护。
- 活动与访问日志记录。
- 配置持久化。
- 支持开发模式与PyInstaller打包后的独立运行。

## Python版本

- 推荐 Python 3.10 及以上。

## 依赖库

- `tkinter`（标准库，用于GUI）
- `threading`（标准库）
- `http.server`、`socket`、`shutil`、`os`、`sys`、`json`、`zipfile`、`time`、`datetime`、`cgi`、`urllib`（标准库）

## 使用方法

1. 安装所需依赖库。
2. 运行 `share.py`：
   ```bash
   python share.py
   ```
3. 在GUI中选择共享目录并启动服务。
4. 在其他设备浏览器访问 `http://<你的IP>:<端口>`。

## 打包说明

如需打包为独立可执行文件（以Windows为例）：
```bash
pyinstaller --onefile --noconsole --add-data "image\change.png;image" --add-data "image\log.ico;image" --add-data "image\log.png;image" --add-data "webserver\webserver.html;webserver" share.py
```
