"""loom.auth：短效 token、token exchange 與租戶注入（第 33、42 章）。

- 有效權限 = 使用者權限 ∩ agent 權限 ∩ 任務範圍。
- 租戶與身分只來自驗證過的 token（伺服器端），tool 參數中不得出現租戶或身分欄位。
- 禁止 token passthrough：下游只接受 audience 為自己的 token，要用 exchange 換一張。
真實系統用非對稱簽章（JWT＋JWKS）；這裡用 HMAC 只為了只靠標準函式庫。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any, Callable

from .core import Middleware, StopRun, ToolResult

FORBIDDEN_ARGS = frozenset({"tenant", "tenant_id", "user_id", "as_user", "org_id"})


class TokenError(Exception):
    pass


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


class AuthServer:
    def __init__(self, issuer: str, key: bytes, clock: Callable[[], int]):
        self.issuer, self.key, self.clock = issuer, key, clock

    def issue(self, sub: str, tenant: str, scope: str, aud: str, ttl: int = 300, **extra: Any) -> str:
        now = self.clock()
        claims = {"iss": self.issuer, "sub": sub, "tenant": tenant, "scope": scope, "aud": aud,
                  "iat": now, "exp": now + ttl, **extra}
        body = _b64(json.dumps(claims, sort_keys=True).encode())
        return body + "." + _b64(hmac.new(self.key, body.encode(), hashlib.sha256).digest())

    def verify(self, token: str, audience: str, leeway: int = 30) -> dict:
        """resource server 每次都要做的四項檢查：簽章、issuer、期限、audience。"""
        body, _, sig = token.partition(".")
        if not hmac.compare_digest(sig, _b64(hmac.new(self.key, body.encode(), hashlib.sha256).digest())):
            raise TokenError("簽章不符")
        claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if claims["iss"] != self.issuer:
            raise TokenError("issuer 不符")
        if self.clock() > claims["exp"] + leeway:
            raise TokenError("token 已過期，需要重新登入")
        if claims["aud"] != audience:
            raise TokenError(f"這張 token 的 audience 是 {claims['aud']}，不是 {audience}")
        return claims

    def exchange(self, subject_token: str, its_aud: str, actor: str, audience: str, scope: str) -> str:
        """只能縮小 scope、換成指定受眾、壽命不超過原 token，並在 act 記下行動者。"""
        c = self.verify(subject_token, its_aud)
        if not set(scope.split()) <= set(c["scope"].split()):
            raise TokenError(f"不能換到原 token 沒有的 scope：{scope}")
        ttl = min(60, c["exp"] - self.clock())
        return self.issue(c["sub"], c["tenant"], scope, audience, ttl, act={"sub": actor})


class AuthMiddleware(Middleware):
    """before_run：驗 token、把身分與租戶注入 deps、算出有效權限。wrap_tool：擋身分參數與越權呼叫。"""

    def __init__(self, auth: AuthServer, audience: str, agent_scopes: dict[str, set[str]]):
        self.auth, self.audience, self.agent_scopes = auth, audience, agent_scopes

    def before_run(self, ctx, user_input):
        try:
            claims = self.auth.verify(ctx.deps.get("token", ""), self.audience)
        except TokenError as exc:
            raise StopRun("blocked", f"身分驗證失敗：{exc}")
        ctx.deps.update(tenant=claims["tenant"], user_id=claims["sub"])   # 覆寫呼叫端傳入的任何同名值
        ctx.state["user_scopes"] = set(claims["scope"].split())
        ctx.state["task_scopes"] = set(ctx.deps.get("task_scope", claims["scope"].split()))

    def effective(self, ctx) -> set[str]:
        """每次都依「目前的」agent 計算：handoff 之後權限跟著換人，不沿用上一個 agent 的。"""
        return ctx.state["user_scopes"] & self.agent_scopes.get(ctx.agent.name, set()) & ctx.state["task_scopes"]

    async def wrap_tool(self, ctx, tc, nxt):
        tool = ctx.find_tool(tc.name)
        if bad := sorted(FORBIDDEN_ARGS & tc.args.keys()):
            return ToolResult("error", f"參數 {bad} 不允許：身分與租戶由 session 決定，不由模型填寫。")
        if tool is not None and tool.scope and tool.scope not in self.effective(ctx):
            return ToolResult("error", f"insufficient_scope：{tc.name} 需要 {tool.scope}，這個 session 沒有。")
        return await nxt(tc)
