# 附錄 E　最小實驗設定與故障後端

## 最小 NGINX 設定

```nginx
daemon off;
worker_processes 1;
error_log logs/error.log debug;
pid logs/nginx.pid;

events {
    worker_connections 1024;
}

http {
    access_log logs/access.log combined;

    upstream lab_backend {
        server 127.0.0.1:9001 weight=2;
        server 127.0.0.1:9002;
        keepalive 8;
    }

    server {
        listen 8080;

        location / {
            proxy_pass http://lab_backend;
            proxy_set_header X-Lab-Request $request_id;
            proxy_connect_timeout 500ms;
            proxy_read_timeout 3s;
        }
    }
}
```

## 可直接執行的故障後端

以下程式只使用 Python 標準函式庫。存成 `backend.py`，分別啟動 A、B 兩個 backend：

```bash
python3 backend.py --port 9001 --name A
python3 backend.py --port 9002 --name B
```

```python
#!/usr/bin/env python3
import argparse
import hashlib
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "nginx-book-lab/1.0"

    def log_message(self, fmt, *args):
        print(f"[{self.server.backend_name}] {self.client_address[0]} "
              f"{fmt % args}", flush=True)

    def number(self, params, name, default, maximum):
        try:
            value = int(params.get(name, [default])[0])
        except (TypeError, ValueError):
            value = default
        return max(0, min(value, maximum))

    def read_body(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            size = 0
        return self.rfile.read(size)

    def send_bytes(self, status, body, content_type="text/plain; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Lab-Backend", self.server.backend_name)
        self.end_headers()
        self.wfile.write(body)

    def raw_response(self, data):
        self.connection.sendall(data)
        self.close_connection = True

    def handle_request(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        path = parsed.path

        if path == "/header-delay":
            delay_ms = self.number(params, "ms", 500, 30_000)
            time.sleep(delay_ms / 1000)
            self.send_bytes(200, f"{self.server.backend_name}: headers delayed "
                            f"{delay_ms}ms\n".encode())
            return

        if path == "/body-delay":
            delay_ms = self.number(params, "ms", 250, 30_000)
            chunks = self.number(params, "chunks", 5, 100)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("X-Lab-Backend", self.server.backend_name)
            self.end_headers()
            for index in range(chunks):
                payload = f"{self.server.backend_name}: chunk {index}\n".encode()
                self.wfile.write(f"{len(payload):x}\r\n".encode())
                self.wfile.write(payload + b"\r\n")
                self.wfile.flush()
                time.sleep(delay_ms / 1000)
            self.wfile.write(b"0\r\n\r\n")
            return

        if path == "/invalid-header":
            self.raw_response(
                b"HTTP/1.1 200 OK\r\n"
                b"Bad Header: deliberately-invalid\r\n"
                b"Content-Length: 3\r\n\r\nbad"
            )
            return

        if path == "/close-mid-body":
            self.raw_response(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/plain\r\n"
                b"Content-Length: 100\r\n\r\npartial"
            )
            return

        if path == "/large":
            size = self.number(params, "n", 1_048_576, 100 * 1024 * 1024)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("X-Lab-Backend", self.server.backend_name)
            self.end_headers()
            block = (self.server.backend_name.encode() * 65_536)[:65_536]
            remaining = size
            while remaining:
                piece = block[:min(len(block), remaining)]
                self.wfile.write(piece)
                remaining -= len(piece)
            return

        if path == "/echo":
            body = self.read_body()
            response = {
                "backend": self.server.backend_name,
                "method": self.command,
                "path": self.path,
                "headers": dict(self.headers.items()),
                "body_bytes": len(body),
                "body_sha256": hashlib.sha256(body).hexdigest(),
            }
            payload = (json.dumps(response, ensure_ascii=False, indent=2)
                       + "\n").encode()
            self.send_bytes(200, payload, "application/json; charset=utf-8")
            return

        self.send_bytes(200, f"{self.server.backend_name}: ok\n".encode())

    do_GET = handle_request
    do_POST = handle_request
    do_PUT = handle_request
    do_DELETE = handle_request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.backend_name = args.name
    print(f"backend {args.name} listening on 127.0.0.1:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
```

## 每個 endpoint 在隔離什麼問題

| Endpoint | 實驗目的 | 建議觀察 |
|---|---|---|
| `/ok` | 正常負載均衡基線 | backend 分布、connection reuse |
| `/header-delay?ms=500` | connect 已完成，但 response header 尚未到 | `proxy_read_timeout`、header time |
| `/body-delay?ms=250&chunks=5` | headers 已到，body 分段抵達 | buffering、streaming、backpressure |
| `/invalid-header` | backend 回傳不合法 header | parser error、502 與 retry policy |
| `/close-mid-body` | 宣告長度與實際 body 不一致 | premature close、已送出 response 後能否 retry |
| `/large?n=104857600` | 大型 response | memory、temporary file、slow client |
| `/echo` | 驗證 method、headers 與 body forwarding | request reconstruction、body replay |

先確認 backend 本身：

```bash
curl -i http://127.0.0.1:9001/ok
curl -i 'http://127.0.0.1:9002/header-delay?ms=500'
curl -N 'http://127.0.0.1:9001/body-delay?ms=200&chunks=4'
printf 'hello' | curl -i -X POST --data-binary @- http://127.0.0.1:9002/echo
```

再經過 NGINX 執行相同請求。每個實驗都帶唯一 request ID，保存 curl 輸出、access/error log 與必要的 strace 片段；只改一個變因，才知道觀察到的差異由哪個機制造成。
