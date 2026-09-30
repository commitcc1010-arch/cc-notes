# 附錄 B　C 語言生存速查

## 必會語法

```c
T *p;              /* 指向 T */
p->field;          /* (*p).field */
void *data;        /* generic pointer，型別由契約決定 */
typedef int (*handler_pt)(request_t *r);
handler_pt next;   /* function pointer */
```

## 半開區間

NGINX大量使用 `[pos, last)`。長度是 `last - pos`；空buffer是 `pos == last`。`start/end`通常描述storage容量，`pos/last`描述當前有效資料。

## `ngx_str_t`

```c
typedef struct {
    size_t  len;
    u_char *data;
} ngx_str_t;
```

`data[len]`不保證是NUL。輸出時使用有長度的format/API，不要直接當`%s`。

## Container-of

Intrusive queue/tree把link嵌進外層struct。已知link地址與欄位offset，可算回object start。它避免wrapper allocation，但要求unlink與lifetime嚴格。

## Return code閱讀法

- `NGX_OK`：本API定義的成功；不一定代表整個request完成。
- `NGX_ERROR`：不可恢復錯誤，通常需finalize/cleanup。
- `NGX_AGAIN`：目前不能前進，保存狀態等待event。
- `NGX_DECLINED`：本handler不處理，讓pipeline繼續。
- `NGX_DONE`：當前控制流停止，常有async ownership未完成。

永遠讀caller如何解釋；名稱不是完整contract。

## Bit fields與flags

大量狀態壓成bit fields。修改前問：誰初始化零值？何時清除？timer/event晚到時此flag是否仍可信？
