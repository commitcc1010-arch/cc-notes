"""loom.memory：檔案式長期記憶（第 12 章）。

模型看到的是虛擬路徑 /memories；harness 依 session 的租戶與使用者（來自 deps，不來自模型）對應到實體目錄。
/memories/org 是組織記憶，agent 只能讀。每次存取都留稽核（只記路徑，不記內容）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

from .core import Tool

VERBS = {"create": "建立", "str_replace": "更新", "delete": "刪除"}
SECRET = re.compile(r"\b(?:\d[ -]?){13,16}\b|密碼|password", re.I)


class MemoryToolError(Exception):
    pass


class MemoryStore:
    def __init__(self, root: Path, max_chars: int = 1_000, ttl_days: dict[str, int] | None = None):
        self.root, self.max_chars = Path(root), max_chars
        self.ttl_days = ttl_days if ttl_days is not None else {"episodes": 30}   # 事件記憶會過期；偏好不會
        self.audit: list[str] = []

    def _dirs(self, deps: dict) -> tuple[Path, Path]:
        tenant, user = deps["tenant"], deps["user_id"]     # KeyError 代表 session 沒注入身分：直接失敗
        base = (self.root / tenant / "users" / user).resolve()
        base.mkdir(parents=True, exist_ok=True)
        return base, (self.root / tenant / "org").resolve()

    def _resolve(self, deps: dict, path: str) -> tuple[Path, Path, bool]:
        parts = PurePosixPath(path).parts
        if parts[:2] != ("/", "memories") or ".." in parts or "%" in path or "\\" in path:
            raise MemoryToolError(f"路徑必須在 /memories 之下，且不可含 .. 或編碼字元：{path}")
        base, org = self._dirs(deps)
        rest, readonly = parts[2:], False
        if rest[:1] == ("org",):
            base, rest, readonly = org, rest[1:], True
        target = base.joinpath(*rest).resolve()
        if not target.is_relative_to(base):                 # 符號連結等繞道：resolve 之後再檢查一次
            raise MemoryToolError(f"路徑逃出了允許的範圍：{path}")
        return base, target, readonly

    def _meta(self, base: Path) -> dict:
        p = base / ".meta.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def handle(self, deps: dict, command: str, path: str, file_text: str = "", old_str: str = "",
               new_str: str = "") -> str:
        who, today = f"{deps.get('tenant')}/{deps.get('user_id')}", int(deps.get("today", 0))
        try:
            out = self._dispatch(deps, today, command, path, file_text, old_str, new_str)
        except MemoryToolError:
            self.audit.append(f"day{today} {who} DENY {command} {path}")   # 越界嘗試正是資安最想看到的訊號
            raise
        self.audit.append(f"day{today} {who} {command} {path}")
        return out

    def _dispatch(self, deps, today, cmd, path, file_text, old_str, new_str) -> str:
        base, target, readonly = self._resolve(deps, path)
        if cmd != "view" and readonly:
            raise MemoryToolError("/memories/org 是組織記憶，agent 只能讀")
        meta = self._meta(base) if not readonly else {}
        rel = target.relative_to(base).as_posix()
        expired = lambda r: (meta.get(r) or {}).get("expires") is not None and today >= meta[r]["expires"]
        if cmd == "view":
            if target.is_dir():
                files = sorted(p.relative_to(target).as_posix() for p in target.rglob("*")
                               if p.is_file() and not p.name.startswith("."))
                return "\n".join(f for f in files if readonly or not expired(f)) or "（目錄是空的）"
            if not target.exists() or expired(rel):
                raise MemoryToolError(f"{path} 不存在")
            return target.read_text(encoding="utf-8")
        if cmd == "create":
            if target.exists():                             # 去重：同一主題只有一個檔
                raise MemoryToolError(f"{path} 已存在。請先 view，再用 str_replace 更新")
            self._check(file_text)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(file_text, encoding="utf-8")
            ttl = self.ttl_days.get(PurePosixPath(rel).parts[0])
            meta[rel] = {"created": today, "expires": today + ttl if ttl else None}
        elif cmd == "str_replace":
            text = target.read_text(encoding="utf-8") if target.is_file() else ""
            if text.count(old_str) != 1:
                raise MemoryToolError(f"old_str 在 {path} 中出現 {text.count(old_str)} 次，必須剛好 1 次")
            self._check(text.replace(old_str, new_str))
            target.write_text(text.replace(old_str, new_str), encoding="utf-8")
        elif cmd == "delete":
            if not target.is_file():
                raise MemoryToolError(f"{path} 不存在")
            target.unlink()
            meta.pop(rel, None)
        else:
            raise MemoryToolError(f"不支援的指令 {cmd}；可用：view、create、str_replace、delete")
        (base / ".meta.json").write_text(json.dumps(meta, ensure_ascii=False))
        return f"已{VERBS[cmd]} {path}"

    def _check(self, text: str) -> None:
        if SECRET.search(text):
            raise MemoryToolError("內容含疑似卡號或密碼，不可寫入長期記憶；請只記偏好，不記憑證")
        if len(text) > self.max_chars:
            raise MemoryToolError(f"內容 {len(text)} 字元，超過單檔上限 {self.max_chars}；請精簡成要點")

    def forget_user(self, tenant: str, user: str) -> int:
        """刪除權：整個使用者目錄移除；回傳刪掉的檔案數。衍生儲存的 fan-out 見第 12 章。"""
        base = (self.root / tenant / "users" / user)
        files = [p for p in base.rglob("*") if p.is_file()] if base.exists() else []
        for p in files:
            p.unlink()
        self.audit.append(f"{tenant}/{user} FORGET {len(files)}")
        return len(files)

    def as_tool(self) -> Tool:
        props = {"command": {"type": "string", "enum": ["view", "create", "str_replace", "delete"]},
                 "path": {"type": "string", "description": "例如 /memories/preferences.md"},
                 "file_text": {"type": "string"}, "old_str": {"type": "string"}, "new_str": {"type": "string"}}
        return Tool("memory", "讀寫這位使用者的長期記憶（偏好、進行中的事）；/memories/org 唯讀",
                    {"type": "object", "properties": props, "required": ["command", "path"]},
                    self.handle, effect="write", intent_fields=("command", "path"))
