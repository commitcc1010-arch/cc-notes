"""loom.mcp：教學版 MCP（第 14 章）。in-process transport，但保留 JSON-RPC 序列化。

只實作 server/discover、tools/list（cursor 分頁）、tools/call；每個 request 自帶協定版本（stateless）。
橋接層 mcp_tools() 把遠端 tool 變成 loom Tool：allowlist、名稱前綴、定義 pin、副作用等級由 loom 端決定。
annotations（readOnlyHint 等）是 server 自己宣告的，不能拿來做安全決策，所以不用它決定 effect。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from .core import Tool, digest

PROTOCOL_VERSION = "2026-07-28"
META_VERSION = "io.modelcontextprotocol/protocolVersion"


class RPCError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code, self.message = code, message


@dataclass
class ServerTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[..., Any]
    annotations: dict[str, bool] = field(default_factory=dict)


class MiniMCPServer:
    def __init__(self, name: str, page_size: int = 50):
        self.info = {"name": name, "version": "1.0.0"}
        self.tools: dict[str, ServerTool] = {}
        self.page_size = page_size

    def tool(self, name: str, description: str, input_schema: dict, **annotations: bool):
        def register(fn):
            self.tools[name] = ServerTool(name, description, input_schema, fn, annotations)
            return fn
        return register

    def handle(self, raw: str) -> str | None:
        """transport 只負責搬字串；所有協定邏輯都在這裡。"""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return self._reply(None, error=(-32700, "Parse error"))
        if "id" not in msg:
            return None                     # notification：不回應
        try:
            result = self._route(msg.get("method", ""), msg.get("params") or {})
        except RPCError as e:
            return self._reply(msg["id"], error=(e.code, e.message))
        return self._reply(msg["id"], result=result)

    def _route(self, method: str, params: dict) -> dict:
        if method == "server/discover":     # 不需要握手，任何時候都能問
            return {"supportedVersions": [PROTOCOL_VERSION], "serverInfo": self.info, "capabilities": {"tools": {}}}
        if params.get("_meta", {}).get(META_VERSION) != PROTOCOL_VERSION:
            raise RPCError(-32000, "Unsupported protocol version")
        if method == "tools/list":
            names = sorted(self.tools)      # 固定順序：對 prompt cache 友善
            start = int(params.get("cursor", 0))
            out: dict[str, Any] = {"tools": [self._describe(self.tools[n]) for n in names[start:start + self.page_size]]}
            if start + self.page_size < len(names):
                out["nextCursor"] = str(start + self.page_size)
            return out
        if method == "tools/call":
            return self._call(params.get("name"), params.get("arguments") or {})
        raise RPCError(-32601, f"Method not found: {method}")

    def _describe(self, t: ServerTool) -> dict:
        return {"name": t.name, "description": t.description, "inputSchema": t.input_schema, "annotations": t.annotations}

    def _call(self, name: str, args: dict) -> dict:
        t = self.tools.get(name)
        if t is None:                       # 呼叫端的錯：協定層錯誤
            raise RPCError(-32602, f"Unknown tool: {name}")
        try:                                # 模型修得好的錯：當成 tool 執行錯誤（isError）回給模型
            value = t.fn(**args)
        except Exception as exc:
            return {"content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}], "isError": True}
        return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}],
                "structuredContent": value, "isError": False}

    @staticmethod
    def _reply(msg_id, result=None, error=None) -> str:
        body: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id}
        if error:
            body["error"] = {"code": error[0], "message": error[1]}
        else:
            body["result"] = result
        return json.dumps(body, ensure_ascii=False)


class InProcessTransport:
    def __init__(self, server: MiniMCPServer):
        self.server, self.wire = server, []

    def send(self, raw: str) -> str | None:
        reply = self.server.handle(raw)
        self.wire.append((raw, reply))      # wire 上的每個位元組都和真的一樣，方便測試與觀察
        return reply


class MCPError(Exception):
    pass


class MiniMCPClient:
    def __init__(self, transport: InProcessTransport):
        self.transport, self.next_id = transport, 0

    def request(self, method: str, params: dict | None = None) -> dict:
        self.next_id += 1
        params = {**(params or {}), "_meta": {META_VERSION: PROTOCOL_VERSION}}
        reply = json.loads(self.transport.send(json.dumps(
            {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}, ensure_ascii=False)))
        assert reply["id"] == self.next_id  # 用 id 對回 request，和 tool_call_id 同一個道理
        if "error" in reply:
            raise MCPError(f"{reply['error']['code']} {reply['error']['message']}")
        return reply["result"]

    def list_tools(self) -> list[dict]:
        tools, cursor = [], None
        while True:                         # cursor 分頁：拿到沒有 nextCursor 為止
            page = self.request("tools/list", {"cursor": cursor} if cursor else {})
            tools += page["tools"]
            if not (cursor := page.get("nextCursor")):
                return tools

    def call_tool(self, name: str, arguments: dict) -> dict:
        return self.request("tools/call", {"name": name, "arguments": arguments})


class ToolExecutionError(Exception):
    pass


def fingerprint(t: dict) -> str:
    """tool 定義（名稱、描述、schema、annotations）的雜湊：任何一個字變了，雜湊就變。"""
    return digest(t, 12)


def mcp_tools(client: MiniMCPClient, prefix: str, allow: dict[str, str],
              pins: dict[str, str] | None = None) -> list[Tool]:
    """allow：遠端 tool 名稱 → loom 的 effect（由審核決定，不採信 annotations）。
    pins：審核時記下的定義雜湊；不符就不載入（防止定義被悄悄改寫，第 14 章的 rug pull）。"""
    def make_fn(remote: str):
        def fn(deps, **args):
            result = client.call_tool(remote, args)
            text = "\n".join(c["text"] for c in result["content"] if c["type"] == "text")
            if result.get("isError"):       # MCP 的 isError → loom 的錯誤觀察
                raise ToolExecutionError(text)
            return text
        return fn

    out = []
    for t in client.list_tools():
        if t["name"] not in allow:
            continue
        if pins is not None and pins.get(t["name"]) != fingerprint(t):
            raise MCPError(f"{prefix}/{t['name']} 的定義和審核時不同，拒絕載入")
        out.append(Tool(f"{prefix}__{t['name']}", f"[{prefix}] {t['description']}", t["inputSchema"],
                        make_fn(t["name"]), effect=allow[t["name"]]))
    return out
