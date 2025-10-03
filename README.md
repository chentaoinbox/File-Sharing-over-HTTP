# File Share Tool

## Overview

This project is a cross-platform file management and sharing tool with both a graphical user interface (GUI) and a web server interface. It allows users to manage files locally and share them over the network via a browser.

## File Structure

```
FileSharingoverHTTP/
├── guiserver/
│   └── guiserver.py      # GUI application (Tkinter)
├── webserver/
│   ├── webserver.py      # Web server for file sharing (HTTP)
│   └── webserver.html    # Static HTML for web interface
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
- **webserver.html**: Local static HTML webpage for web interface.

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
- `PIL`, `qrcode`

### Library Usage

- **tkinter**: Used to build the local GUI (windows, Treeview, buttons, etc.).
- **threading**: GUI, web service, and log writing each run in independent threads to avoid blocking the main thread.
- **http.server**: Provides the basic HTTP service framework; `FileServer` inherits from `SimpleHTTPRequestHandler` to handle requests.
- **socket**: Detects local IP, checks/occupies ports, implements port open/close control logic.
- **shutil / os / json / time / datetime**: File operations, copy/delete, configuration serialization, timestamp and log processing.
- **zipfile**: Generates ZIP packages for download (supports folders and single PDF packaging).
- **cgi / urllib**: Handles multipart/form-data uploads and URL decoding.
- **PIL (Pillow)**: Used in GUI for loading, cropping, and displaying images (Image, ImageTk). Pillow is a third-party dependency that must be installed separately.
- **qrcode**: 

## Installation

Install required third-party packages:

```powershell
pip install pillow
```

For building a standalone executable:

```powershell
pip install pyinstaller
```

## Running the Application

From the repository root (folder containing `share.py`):

```powershell
python share.py
```

## Building Executable

Create a single-file executable using PyInstaller:

```powershell
pyinstaller --onefile --noconsole --name="FileSharingoverHTTP" --icon=image\log.ico --add-data "image\change.png;image" --add-data "image\log.ico;image" --add-data "image\log.png;image" --add-data "webserver\webserver.html;webserver" share.py
```

## Configuration

The application uses `config/config.txt` for runtime settings. Example configuration:

```
dir=E:\Share
port=8000
pw_enabled=1
password=123456
```

- `dir`: Path to the shared directory
- `port`: HTTP port (default: 8000)
- `pw_enabled`: 1 to enable password protection, 0 to disable
- `password`: Password string when `pw_enabled=1`

## Programmatic API

You can import the webserver module to control the HTTP server:

```python
from webserver import webserver

# Start the server
webserver.start_server()

# Stop the server
webserver.force_stop_server()

# Refresh configuration
webserver.refresh_all()
```

## HTTP Endpoints & Examples

The web server exposes several HTTP endpoints used by the GUI and by clients. Below is a concise summary with example usages and common response codes.

- GET /list?dir=<relative_path>
	- Returns a JSON array of items for the given (relative) directory under the shared `dir`.
	- Example (curl):

```powershell
curl "http://localhost:8000/list?dir=subfolder"
```

- GET /config
	- Returns JSON: {"enableLogin": true/false}

- POST /login
	- Body: JSON {"password": "..."}
	- Returns JSON {"success": true/false}

- POST /upload?dir=<relative_path>
	- multipart/form-data file upload. Field name expected: `file`.
	- Example (curl):

```powershell
curl -F "file=@C:\path\to\file.txt" "http://localhost:8000/upload?dir=subfolder"
```

- POST /newfolder?dir=<relative_path>
	- Body: JSON {"name": "newFolderName"}
	- Creates a folder under the shared directory (relative path allowed).

- GET /port/check  GET /port/open  GET /port/close
	- Controls and queries whether the server port is available / opened by the application.
	- Returns JSON with status and port field.

- GET /<file-or-folder-path> or /image/<image>
	- Download a file, or serve static project assets.

- GET /<folder>.zip
	- Streams a ZIP archive of the folder, or packages a single PDF file into a zip if a PDF path is requested.

- DELETE /<path>
	- Deletes a file or folder under the shared directory. Returns 204 on success.

Common response codes:
- 200 OK — normal JSON or file stream response.
- 204 No Content — successful operations like upload/newfolder/delete that do not have a body.
- 400 Bad Request — malformed request or missing parameters.
- 403 Forbidden — attempted access outside the configured shared directory.
- 404 Not Found — requested file/folder not found.
- 500 Internal Server Error — server-side error.

Notes:
- All `dir` parameters are relative to the configured shared directory (`config/config.txt` -> `dir`). Absolute paths are not permitted in requests and will be rejected.

## QR Code generation (GUI)

The GUI generates a QR code for quick access to the service address. The implementation uses the `qrcode` Python package and Pillow for rendering. If you plan to run the GUI and want QR generation, install:

```powershell
pip install qrcode[pil]
```

If `qrcode` is not installed, the GUI will still operate but the QR code feature will be disabled.

## Headless / CLI usage

If you want to run only the HTTP service without the GUI, you can run the web server module directly or import and call it from a script.

From repository root (start service only):

```powershell
python webserver\webserver.py
```

Or programmatically (recommended for embedding):

```powershell
python -c "from webserver import webserver; webserver.start_server(); import time; print('server started'); time.sleep(86400)"
```

Running the module directly prints interactive hints in the console and allows starting/stopping via keyboard when run as a script.

## Requirements file

Add a `requirements.txt` for easier environment setup. Suggested contents:

```
Pillow
qrcode[pil]
pyinstaller  # only needed if you package
```

Install dependencies with:

```powershell
pip install -r requirements.txt
```

## Logs and file paths (packaged vs development)

- Development mode (running `python share.py`):
	- `config/` and `log/` are relative to the project directory where `share.py` resides.

- Packaged mode (PyInstaller `--onefile`):
	- The bundle extracts resources to a temporary folder referenced by `sys._MEIPASS`. The code attempts to locate resources (images, webserver.html) using `sys._MEIPASS` or `sys.executable`. Log files are written to a `log/` directory next to the executable.

When troubleshooting missing images or HTML after packaging, confirm `--add-data` entries and check the runtime paths.

## Expanded Troubleshooting

- Uploads failing with 400 or no file received:
	- Ensure the client sends the multipart form field named `file` and includes the correct `Content-Type` header.

- ZIP creation incomplete or fails when downloading folders:
	- Large folders take longer to stream; check server logs for exceptions. For very large content, consider pre-creating a zip file instead of on-the-fly streaming.

- Windows: GUI icons do not appear or fail to load:
	- Verify image paths. When running from PyInstaller bundle, images must be added via `--add-data` and referenced correctly in code (the project already checks `sys._MEIPASS`).

- Port check always shows occupied even after stopping server:
	- The code may leave a bound socket in `FileServer.port_socket`; the `force_stop_server()` function attempts to close it. If the process crashed, the OS may still hold the port briefly — wait a few seconds or choose a different port.

## Final notes

If you'd like, I can:
- Generate a `requirements.txt` file and commit it.
- Create an extra `DEVELOPER.md` that documents internal module APIs and key functions (with argument types and examples).
- Produce curl and PowerShell scripts for automated testing of the endpoints.


## Security Notes

- This tool is designed for LAN use and is not hardened for public internet exposure.
- Passwords are stored in plain text in `config/config.txt`.
- Always use strong passwords when enabling password protection.

## Troubleshooting

- **Port already in use**: Change the port in `config/config.txt`
- **Firewall blocks**: Allow the application through Windows Firewall
- **File permission errors**: Ensure the shared directory is accessible
- **Encoding issues**: Set console to UTF-8 (Windows: `chcp 65001`)

## License

This project does not include an explicit open-source license file. Please add a LICENSE file if you plan to publish or distribute this project.


