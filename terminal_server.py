import os, sys, pty, fcntl, termios, signal
import threading, json, time, base64, hashlib
import urllib.parse, urllib.request
import select as _select
import struct as _struct
import socket as _sock_mod
from pathlib import Path

PORT          = int(os.environ.get("PORT", 7681))
HOST          = "0.0.0.0"
UPLOAD_DIR    = Path("/tmp/teamdev_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
KEEPALIVE_URL = os.environ.get("KEEPALIVE_URL", "")
TERMINAL_PASSWORD = os.environ.get("TERMINAL_PASSWORD", "TeamDev@2026")

WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

def ws_accept_key(key):
    return base64.b64encode(
        hashlib.sha1((key + WS_MAGIC).encode()).digest()
    ).decode()

def ws_handshake(key):
    return (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {ws_accept_key(key)}\r\n"
        "\r\n"
    ).encode()

def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        try:
            chunk = sock.recv(n - len(buf))
        except Exception:
            return buf
        if not chunk:
            return buf
        buf += chunk
    return buf

def ws_recv(sock):
    try:
        h = _recv_exact(sock, 2)
        if len(h) < 2:
            return None, None
        b1, b2 = h
        opcode = b1 & 0x0F
        masked = bool(b2 & 0x80)
        length = b2 & 0x7F
        if length == 126:
            length = int.from_bytes(_recv_exact(sock, 2), 'big')
        elif length == 127:
            length = int.from_bytes(_recv_exact(sock, 8), 'big')
        mask = _recv_exact(sock, 4) if masked else b'\x00\x00\x00\x00'
        data = _recv_exact(sock, length)
        if masked:
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        return opcode, data
    except Exception:
        return None, None

def ws_send(sock, data, opcode=0x2):
    try:
        n = len(data)
        hdr = bytes([0x80 | opcode])
        if n < 126:
            hdr += bytes([n])
        elif n < 65536:
            hdr += bytes([126]) + n.to_bytes(2, 'big')
        else:
            hdr += bytes([127]) + n.to_bytes(8, 'big')
        sock.sendall(hdr + data)
        return True
    except Exception:
        return False

def ws_json(sock, obj):
    return ws_send(sock, json.dumps(obj).encode('utf-8'), 0x1)

class PtySession:
    def __init__(self, sock, cols=200, rows=50):
        self.sock  = sock
        self.cols  = cols
        self.rows  = rows
        self.pid   = None
        self.fd    = None
        self.alive = True

    def start(self):
        shell = os.environ.get("SHELL", "/bin/bash")
        env = os.environ.copy()
        env.update({
            "TERM":      "xterm-256color",
            "COLORTERM": "truecolor",
            "LANG":      "en_US.UTF-8",
            "LC_ALL":    "en_US.UTF-8",
            "COLUMNS":   str(self.cols),
            "LINES":     str(self.rows),
            "PS1":       r"\[\033[01;32m\]teamdev\[\033[0m\]@\[\033[01;36m\]ubuntu-24\[\033[0m\]:\[\033[01;33m\]\w\[\033[0m\]\$ ",
            "HOME":      str(UPLOAD_DIR),
        })
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            try:
                os.chdir(str(UPLOAD_DIR))
            except Exception:
                pass
            try:
                os.execvpe(shell, [shell, "--login"], env)
            except Exception:
                os.execvpe("/bin/sh", ["/bin/sh"], env)
        else:
            self._set_winsize(self.cols, self.rows)
            threading.Thread(target=self._read_loop, daemon=True).start()

    def _set_winsize(self, cols, rows):
        if self.fd is None:
            return
        try:
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ,
                        _struct.pack('HHHH', rows, cols, 0, 0))
        except Exception:
            pass

    def resize(self, cols, rows):
        self.cols, self.rows = cols, rows
        self._set_winsize(cols, rows)

    def write(self, data):
        if self.fd is not None:
            try:
                os.write(self.fd, data)
            except OSError:
                pass

    def _read_loop(self):
        while self.alive:
            try:
                r, _, _ = _select.select([self.fd], [], [], 0.05)
                if r:
                    data = os.read(self.fd, 8192)
                    if data:
                        ws_json(self.sock, {
                            "type": "output",
                            "data": base64.b64encode(data).decode()
                        })
            except OSError:
                break
            except Exception:
                continue
        ws_json(self.sock, {"type": "exit"})
        self.alive = False

    def kill(self):
        self.alive = False
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
            except Exception:
                pass
        if self.fd:
            try:
                os.close(self.fd)
            except Exception:
                pass

HTML_FILE     = Path(__file__).parent / "teamdev_terminal_ui.html"
MANIFEST_FILE = Path(__file__).parent / "manifest.json"

def http_resp(sock, status, body, ctype="text/html; charset=utf-8"):
    reason = {200:"OK", 404:"Not Found", 500:"Error"}.get(status,"")
    hdr = (
        f"HTTP/1.1 {status} {reason}\r\n"
        f"Content-Type: {ctype}\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "\r\n"
    ).encode()
    sock.sendall(hdr + body)

def serve_html(sock):
    if not HTML_FILE.exists():
        http_resp(sock, 404, b"UI file missing")
        return
    html = HTML_FILE.read_text(encoding="utf-8")
    inject = f"<script>window.__TERMINAL_PASSWORD__={json.dumps(TERMINAL_PASSWORD)};</script>"
    html = html.replace("</head>", inject + "\n</head>", 1)
    http_resp(sock, 200, html.encode("utf-8"))

def handle_http(sock, method, path, buf):
    try:
        if method == "GET" and path in ("/", "/index.html"):
            serve_html(sock)
        elif method == "GET" and path == "/manifest.json":
            if MANIFEST_FILE.exists():
                http_resp(sock, 200, MANIFEST_FILE.read_bytes(), "application/manifest+json")
            else:
                http_resp(sock, 404, b"{}", "application/json")
        elif method == "GET" and path == "/health":
            http_resp(sock, 200, b"OK", "text/plain")
        elif method == "POST" and path == "/upload":
            hdr_end = buf.index(b"\r\n\r\n") + 4
            body = buf[hdr_end:]
            raw_hdrs = buf[:hdr_end].decode('utf-8', errors='replace')
            for line in raw_hdrs.split('\r\n'):
                if line.lower().startswith('content-length:'):
                    cl = int(line.split(':', 1)[1].strip())
                    while len(body) < cl:
                        body += sock.recv(65536)
                    break
            p = json.loads(body)
            dest = UPLOAD_DIR / p.get("name", "file.bin")
            dest.write_bytes(base64.b64decode(p["data"]))
            http_resp(sock, 200, json.dumps({"ok":True,"path":str(dest)}).encode(), "application/json")
        else:
            http_resp(sock, 404, b"Not found")
    except Exception as e:
        try: http_resp(sock, 500, str(e).encode())
        except: pass

def ws_loop(sock, session):
    try:
        while True:
            opcode, data = ws_recv(sock)
            if opcode is None or opcode == 0x8:
                break
            if opcode == 0x9:
                ws_send(sock, data, 0xA)
                continue
            if opcode not in (0x1, 0x2):
                continue
            try:
                msg   = json.loads(data.decode('utf-8'))
                mtype = msg.get("type", "")
                if mtype == "input":
                    session.write(base64.b64decode(msg["data"]))
                elif mtype == "resize":
                    session.resize(int(msg.get("cols",200)), int(msg.get("rows",50)))
                elif mtype == "ping":
                    ws_json(sock, {"type":"pong"})
                elif mtype == "upload":
                    name    = msg.get("name","file.bin")
                    content = base64.b64decode(msg["data"])
                    dest    = UPLOAD_DIR / name
                    dest.write_bytes(content)
                    ws_json(sock, {"type":"upload_ok","name":name,"path":str(dest),"size":len(content)})
                    ws_json(sock, {"type":"output","data":base64.b64encode(
                        f"\r\n\033[1;32m✓ Uploaded → {dest}\033[0m\r\n".encode()
                    ).decode()})
            except Exception as e:
                print(f"[WS msg] {e}")
    finally:
        session.kill()

def handle_conn(sock, addr):
    try:
        sock.setsockopt(_sock_mod.IPPROTO_TCP, _sock_mod.TCP_NODELAY, 1)
        sock.setsockopt(_sock_mod.SOL_SOCKET,  _sock_mod.SO_KEEPALIVE, 1)

        sock.settimeout(20.0)
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                return
            buf += chunk
        sock.settimeout(None)

        raw   = buf.decode('utf-8', errors='replace')
        lines = raw.split('\r\n')

        parts = lines[0].split()
        if len(parts) < 2:
            return
        method = parts[0].upper()
        path   = urllib.parse.urlparse(parts[1]).path

        headers = {}
        for line in lines[1:]:
            if ':' in line:
                k, v = line.split(':', 1)
                headers[k.strip().lower()] = v.strip()

        is_ws = 'websocket' in headers.get('upgrade', '').lower() or \
                'websocket' in raw.lower()

        if is_ws:
            ws_key = headers.get('sec-websocket-key', '')
            if not ws_key:
                return
            sock.sendall(ws_handshake(ws_key))
            session = PtySession(
                sock,
                cols=int(headers.get('x-cols', 200)),
                rows=int(headers.get('x-rows', 50))
            )
            session.start()
            ws_loop(sock, session)
        else:
            handle_http(sock, method, path, buf)

    except Exception as e:
        print(f"[ERR] {addr}: {e}")
    finally:
        try:
            sock.close()
        except Exception:
            pass

def keepalive_loop():
    if not KEEPALIVE_URL:
        return
    print(f"[KA] Keepalive → {KEEPALIVE_URL}")
    while True:
        time.sleep(25)
        try:
            urllib.request.urlopen(KEEPALIVE_URL + "/health", timeout=10)
            print(f"[KA] ✓ ping ok")
        except Exception as e:
            print(f"[KA] ✗ {e}")

class TermServer:
    def __init__(self, host, port):
        self.sock = _sock_mod.socket(_sock_mod.AF_INET, _sock_mod.SOCK_STREAM)
        self.sock.setsockopt(_sock_mod.SOL_SOCKET, _sock_mod.SO_REUSEADDR, 1)
        try:
            self.sock.setsockopt(_sock_mod.SOL_SOCKET, _sock_mod.SO_REUSEPORT, 1)
        except Exception:
            pass
        self.sock.bind((host, port))
        self.sock.listen(256)
        self.host = host
        self.port = port

    def serve_forever(self):
        print(f"╔══════════════════════════════════════════╗")
        print(f"║  TeamDev Terminal Server  v2.0.50         ║")
        print(f"║  Ubuntu 24.04 · PTY · WebSocket · sudo   ║")
        print(f"║  Made By @TeamDevXBots              ║")
        print(f"╚══════════════════════════════════════════╝")
        while True:
            try:
                conn, addr = self.sock.accept()
                threading.Thread(
                    target=handle_conn, args=(conn, addr), daemon=True
                ).start()
            except KeyboardInterrupt:
                print("\n[TeamDev] Stopped.")
                break
            except Exception as e:
                print(f"[accept] {e}")

if __name__ == "__main__":
    if KEEPALIVE_URL:
        threading.Thread(target=keepalive_loop, daemon=True).start()
    TermServer(HOST, PORT).serve_forever()
