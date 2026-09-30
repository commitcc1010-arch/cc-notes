# 附錄 F　21 天核心閱讀計畫

| 天 | 章節 | 當日輸出 |
|---:|---|---|
| 1 | 1–2 | 跑通兩backend proxy，保存黃金路徑log |
| 2 | 3–4 | 完成object/callback cards |
| 3 | 5–7 | 畫main→cycle與generation |
| 4 | 8–9 | 實驗worker crash與reload |
| 5 | 10–11 | 追accept到HTTP init |
| 6 | 12–14 | 畫epoll/event loop |
| 7 | 15–16 | timer tree與slow client |
| 8 | 17–18 | request object與分段request line |
| 9 | 19–20 | header安全與location matrix |
| 10 | 21 | phase trace |
| 11 | 22–24 | body、filter、finalize |
| 12 | 25–27 | proxy/upstream/connect |
| 13 | 28–29 | 手算並實測load balancing |
| 14 | 30 | failure/retry/idempotency |
| 15 | 31–32 | keepalive與buffering |
| 16 | 33–35 | cache、pool、資料結構 |
| 17 | 36–38 | buffer/shared/module |
| 18 | 39 | Hello module |
| 19 | 40–42 | Access或filter module擇一 |
| 20 | 44–45 | fault matrix與歷史fix |
| 21 | 46–48 | 不看書重畫全流程與遷移模型 |

每天最後用十五分鐘口述：「物件、狀態、下一callback、timeout、cleanup」。說不清楚的地方才回源碼補。
