# 附錄 I　版本、資料來源與閱讀原則

## 固定版本

- NGINX tag：`release-1.31.5`
- Commit：`231a60ee3e90a43b829b9ca0a3013a8359b98d7e`
- 主要平台：Linux epoll
- 主線協定：HTTP/1.1 reverse proxy

## 第一手資料

- 官方源碼：<https://github.com/nginx/nginx/tree/release-1.31.5>
- 官方 Development Guide：<https://nginx.org/en/docs/dev/development_guide.html>
- 官方 HTTP Load Balancing：<https://nginx.org/en/docs/http/load_balancing.html>
- 官方 Beginner's Guide：<https://nginx.org/en/docs/beginners_guide.html>
- 官方指令文件：<https://nginx.org/en/docs/>

## 方法

技術敘述以固定tag源碼與官方文件交叉核對。每章先用可執行的 Python 小模型隔離一個核心設計，再逐欄映射到 NGINX 的 C object、callback 與生命週期；Python 是概念等價模型，不是 NGINX 的逐行翻譯。其後直接內嵌同一主題的官方真實源碼視窗、檔案與行號，因此離線閱讀也能完成第一輪理解；外部連結只供繼續追完整上下文。

讀源碼的核心方法來自問題驅動：先追一條user-visible path；遇到epoll、紅黑樹、狀態機、pool再即時學背景；理解後用實驗、module或bug reproduction驗收。這避免把本書變成脫離場景的C、OS或算法百科。

本書內嵌的 C 摘錄來自上述固定版本的官方 repository；完整 copyright notices 與授權條款以該 release 的 `LICENSE` 為準。引用與修改時請遵守上游授權。本書內容是教學整理，不替代官方安全公告、版本 release notes 或 production 操作文件。
