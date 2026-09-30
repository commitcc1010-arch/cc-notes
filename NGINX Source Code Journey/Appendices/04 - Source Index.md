# 附錄 D　源碼檔案與核心函式索引

## 啟動與程序

| 問題 | 主要座標 |
|---|---|
| 程式入口 | `src/core/nginx.c::main` |
| 建立configuration generation | `src/core/ngx_cycle.c::ngx_init_cycle` |
| Master loop | `src/os/unix/ngx_process_cycle.c::ngx_master_process_cycle` |
| Worker loop | `src/os/unix/ngx_process_cycle.c::ngx_worker_process_cycle` |

## Event

| 問題 | 主要座標 |
|---|---|
| 接受連線 | `src/event/ngx_event_accept.c::ngx_event_accept` |
| 一輪scheduler | `src/event/ngx_event.c::ngx_process_events_and_timers` |
| Linux epoll wait | `src/event/modules/ngx_epoll_module.c::ngx_epoll_process_events` |
| Timer tree | `src/event/ngx_event_timer.c` |

## HTTP

| 問題 | 主要座標 |
|---|---|
| 初始化HTTP connection | `src/http/ngx_http_request.c::ngx_http_init_connection` |
| 建request | `ngx_http_create_request` |
| Request line/header | `ngx_http_process_request_line` / `ngx_http_process_request_headers` |
| Parser | `src/http/ngx_http_parse.c` |
| Location | `ngx_http_core_find_location` |
| Phase engine | `ngx_http_core_run_phases` |
| Finalize/keepalive/free | `ngx_http_finalize_request` / `ngx_http_set_keepalive` / `ngx_http_free_request` |

## Upstream

| 問題 | 主要座標 |
|---|---|
| 建立/啟動 | `ngx_http_upstream_create` / `ngx_http_upstream_init` |
| 連backend | `ngx_http_upstream_connect` / `ngx_event_connect_peer` |
| Retry | `ngx_http_upstream_next` |
| Weighted RR | `ngx_http_upstream_get_peer` |
| Keepalive | `ngx_http_upstream_keepalive_module.c` |
| Buffer pipe | `src/event/ngx_event_pipe.c` |
| Cache | `src/http/ngx_http_file_cache.c` |

## Core primitives

Pool看`ngx_palloc.c`；buffer/chain看`ngx_buf.h`與`ngx_output_chain.c`；array/list/queue/hash/rbtree/radix看`src/core/ngx_*`對應檔；shared memory/slab/lock看`ngx_shmem.c`、`ngx_slab.c`、`ngx_shmtx.c`。
