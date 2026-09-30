# 附錄 C　Linux Syscall 與網路速查

| Syscall | 在主線中的角色 | 常見結果 |
|---|---|---|
| `socket` | 建立listen/upstream socket | fd或error |
| `bind` | 綁local address/port | address in use/permission |
| `listen` | 建立accept queue入口 | backlog受kernel限制 |
| `accept4` | 取得client connected fd | fd、EAGAIN、EMFILE |
| `connect` | 啟動backend TCP連線 | 0、EINPROGRESS、error |
| `recv` | 讀byte stream | bytes、0 EOF、EAGAIN |
| `writev` | 送多段memory buffers | partial bytes、EAGAIN |
| `sendfile` | 送file range到socket | partial bytes、EAGAIN |
| `epoll_ctl` | 維護interest set | add/mod/del |
| `epoll_wait` | 等ready fd或timer timeout | ready events、EINTR |
| `mmap` | shared memory/file mapping | process-visible region |
| `fork` | 建worker | child複製address space/COW |

## TCP 狀態排障

- `SYN-SENT` 很久：route/firewall/backend accept問題。
- `ESTABLISHED`但header time高：application/queue慢。
- `CLOSE-WAIT`多：peer已FIN，本端未close。
- `TIME-WAIT`多：主動close與連線重用策略。
- RST：peer abort、未讀資料close或中間設備。

## Readiness檢查表

Read-ready不保證完整消息；write-ready不保證整個buffer可送；connect write-ready不保證成功；timer deadline不保證real-time準點。所有操作都要讀實際return value。
