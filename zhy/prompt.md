1. 剔除无关文件夹.mid10.json中,parent_id不为8614f137547f4e46b8557ae8d3b1e1f5的全部剔除
2. 找到法律状态和LEGAL_STATUS的映射关系表
3. 🧐摘要如何获取?当前只获取摘要部分的文件和图片就行了
4. 直接根据现有信息构建excel表
5. 做cron,实现每月自动更新最新数据.
6. 参数合规化程序

1. 
编写一个流程文件
阅读zhy\data\tmp\mid10.json中的字段,找出所有parent_id字段值不为8614f137547f4e46b8557ae8d3b1e1f5的记录
然后在zhy\data\output\folder_patents_hybrid文件夹,删除所有被找到的文件夹目录
比如说
```json
{
    "paper_count" : 0,
    "patent_count" : 7,
    "folder_id" : "0b77a83bc2554d52b66e6350cb8729f3",
    "parent_id" : "-root",
    "folder_name" : "太子参环肽B工艺技术全景分析",
    "folder_desc" : "",
    "folder_auto_update" : false,
    "has_new_patents" : false,
    "patent_count_ts" : 1761115341425,
    "created_at" : "2025-10-22T06:42:20.103Z",
    "last_update_change_ts" : 0,
    "updated_at" : "2026-04-10T01:11:53.109Z",
    "folder_expansion" : false,
    "can_edit" : true,
    "can_delete" : true,
    "can_copy" : true,
    "can_move" : true,
    "can_add" : true,
    "can_edit_data" : true,
    "can_read_field" : true,
    "space_id" : "ccb6031b05034c7ab2c4b120c2dc3155",
    "share_count" : 0,
    "root_folder" : true,
    "field_transform_infos" : [ ],
    "not_match_sub_folder" : false,
    "free_share_status" : false,
    "ma_count" : 0,
    "drug_count" : 0,
    "clinical_count" : 0,
    "vc_count" : 0,
    "bio_count" : 0,
    "clinical_trial_result_count" : 0,
    "mr_count" : 0
  }
```
这里的parent_id为"-root",不为8614f137547f4e46b8557ae8d3b1e1f5,所以这个文件夹应该被删除.找到对应的zhy\data\output\folder_patents_hybrid\ccb6031b05034c7ab2c4b120c2dc3155_0b77a83bc2554d52b66e6350cb8729f3,删除即可.

2. 已经解决.见zhy\data\tmp\mid1.json
未来最好再做成:程序进入页面以后自动捕获,自动获取这个映射表.因为映射表很有可能更新.映射表按文件夹获取,每切换一个文件夹,就更新一次映射表(所以要多发一个GET),以下是GET容
```md
请求 URL
https://basic-service.zhihuiya.com/core-basic-api/analytics/config/legal-status
请求方法
GET
状态代码
200 OK
Remote Address
81.70.127.178:443
引用站点策略
strict-origin-when-cross-origin
access-control-allow-origin
*
access-control-expose-headers
content-disposition
content-encoding
gzip
content-type
application/json;charset=utf-8
date
Fri, 10 Apr 2026 03:36:22 GMT
set-cookie
tgw_l7_route=f867098e173da53233789f8c2d2640c9; Expires=Fri, 10-Apr-2026 03:36:52 GMT; Path=/; sameSite=None; Secure
vary
Origin
vary
Access-Control-Request-Method
vary
Access-Control-Request-Headers
vary
Accept-Encoding, User-Agent
via
kong/0.14.1
x-client-id
3eea55caeb6247c89952af43ffd8dd03
x-correlation-id
be5b2b01-acbb-4390-9612-3ce8abc34c6f
x-kong-proxy-latency
1
x-kong-upstream-latency
4
:authority
basic-service.zhihuiya.com
:method
GET
:path
/core-basic-api/analytics/config/legal-status
:scheme
https
accept
application/json, text/plain, */*
accept-encoding
gzip, deflate, br, zstd
accept-language
zh-CN,zh;q=0.9,ja;q=0.8,en-US;q=0.7,en-IN;q=0.6,en;q=0.5,ru;q=0.4,en-GB;q=0.3,bn-IN;q=0.2,bn;q=0.1
authorization
Bearer eyJhbGciOiJSUzI1NiJ9.eyJqdGkiOiJlOTI3NWY4Yy05ODlmLTRhNWMtODJkOC01YmZhODQ1OTMxODAiLCJpc3MiOiJwYXRzbmFwIiwic3ViIjoiZWZhYTI4YzUwZWRlNGRlNjhlMjkyNmU2NmFlMTc1ZGIiLCJpYXQiOjE3NzU3OTE4MTEsImV4cCI6MTc3NTc5MzYxMSwidGVuYW50X2lkIjoiYTgwNzMwMDEzYTI0NGRkMDhmMTc1ZTI1YTRkM2E4ODIiLCJwcm9kdWN0IjoiZjIwN2NhNjBlYzA2NGVkYmJjYmMyNjk5Nzk4NTQwMGEiLCJ1c2VyX2lkIjoiZWZhYTI4YzUwZWRlNGRlNjhlMjkyNmU2NmFlMTc1ZGIiLCJzZXNzaW9uIjoiNTNiM2VhN2YtNmFjZi00NzAzLTliMDAtZmM5ZDVkODNhMGExIiwiY2xpZW50X2lkIjoiM2VlYTU1Y2FlYjYyNDdjODk5NTJhZjQzZmZkOGRkMDMiLCJhdXRob3JpdGllcyI6WyI0NDMwMiIsIjF5ZXkiLCIzMWM4IiwiMzV6dSIsInQwMDA4IiwiYTA2cSIsIjQwMTAwIiwiNDIwMDAiLCI3ajY2IiwiZ3F3ZyIsIjNhcHQiLCI0MDUwMCIsIjF3emgiLCI0MDUwNiIsInQwMDAzIiwiMzZ0ZyIsIjNjZGoiLCI0MDkwMCIsIjQyODAwIiwiNDA1MDMiLCI4MDAwMyIsInN2dHUiLCI4MDAwMSIsIjViMm8iLCI4MDAwNyIsIjNiYzYiLCIzc20yIiwiN3VjaSIsImIwMDAzIiwiM3hvMCIsIjNweTQiLCIyMDEwMCIsIjQ1MTAxIiwiM2JjZSIsIjN5cHoiLCI0MzYwMSIsIjYwMDZjIiwiNDMyMDYiLCIyMDEwNiIsIjNjZWsiLCJjb2c3IiwiMzFsMyIsIjFwbjAiLCIxd3J6IiwiMThmbiIsIjNjdWYiLCIzcG5zIiwiMzhwcCIsIjYwMGhjIiwiNDIxMDIiLCIxanQwIiwiNDI1MDAiLCIzYzVhIiwiNDQwMDAiLCIzeXpkIiwiMXBubCIsIjQyNTA3IiwiNDI5MDMiLCJuMDAwMSIsIjYwMDdjIiwiN2o2cSIsIjNhdDMiLCIzMTM1IiwiMTFjMSIsIjFwZzYiLCIxdzFtIiwiMzFjcSIsIjYwMGljIiwiNjAwamMiLCJxZWJiIiwiMWNlaSIsIjNhY28iLCI3cXEwIiwiNDEwMDQiLCIzMHNnIiwiMWpieSIsIjQxMDAxIiwiNDE4MDAiLCI0MTAwNyIsIjgwMDA5IiwiMjMzMTUiLCI2MDA4YyIsIjQyNjE0IiwiODAwMTQiLCIxOHIxIiwiMzNyMyIsIjMxM2QiLCI2MDBiYyIsIjMwMWIiLCIzMmg3IiwiYzBjbSIsIjF3dHEiLCIzNng5IiwiM2NmeiIsIjNwcjkiLCIxajFiIiwiMzF1YSIsIjMwbDgiLCIxNmRjNDhiNjk5NTM0ZDg0YjlhODEyYzJlZDBlMDczZCIsIjFwZm8iLCIyMTUwMSIsIjQyMjAzIiwiNDIzMjQiLCI0NjQwMSIsIjF3NGwiLCJtbmQ3IiwiNjAwMWMiLCI0MjYwNCIsIjFqbjEiLCI0MDcwNCIsIjE4cmUiLCI0MDcwMSIsIjE1Y2YiLCI4MDIwMCIsIjNwOGUiLCI0MTkwNSIsIjN4YWgiLCIxMWNlIiwiM2J4NyIsIjN2bXkiLCIzcGlsIiwiY291cnNlX3B1YmxpY19kYWNiYmExMmZhZmMxZDI2NWZiOWZlMWE1Nzc0ZGY5NCIsIjExZTIiLCI1bW13IiwiMXlpZiIsIjQzMDAzIiwiMjAzMDAiLCI0MjMxMyIsIjMyYjUiLCI0MTEwMCIsIjF0ajkiLCIzMWdmIiwiMXdmdSIsIjQyMzE1IiwiMjA3MDAiLCIxd2g4IiwiM2cxNCIsIjQwODExIiwiNDA0MDkiLCIxOHJuIiwiMWoyeSIsIjFqZGsiLCI0MDgwOCIsIjNqNWEiLCIzMG5nIiwiMjAxMTMiLCIzbTY2IiwiNDQ2MDEiLCIzY2JuIiwiMWdwbCIsIjF5MXoiLCIzM3Y0IiwibXpseCIsIjQwNDAxIiwiMzE4NiIsIjQwNDA3Iiwic3l5biIsIjQyNzAwIiwiMzZ6biIsIjQwNDA0IiwiNDA4MDAiLCJhMDVjIiwiNDMxMDIiLCIyMDAwNCIsIjIwNDAwIiwiNzltZSIsIjQzNTAxIiwiMjI3MDUiLCIyMDAwMCIsIjQwNTEzIiwiNDM5MDMiLCI0MTYwMCIsIjQwNTEwIiwiMjA4MDEiLCI3ajU4IiwiMjAwMDgiLCIyMDAwNiIsIjF3aGoiLCIxMTR6IiwiMzJiaSIsIjM4cDQiLCJkMDAwMSIsIjMyYmgiLCI2MDUwMiIsImQwMDAwIiwiM2MxbSIsIjNjc3EiLCIxeWRrIl0sInByb2R1Y3RzIjpbImNvcGlsb3QiLCJjaGVtaWNhbCIsImVjNGJkZjliNzZhOTRhODNhZGU1YzA2MjJjMzQ2MDYyIiwiYzEwODMyMzQ5Zjg3NGM4ZmFiZDBlOWNhNzRhMmQ5MmUiLCJiYWU5MTM3N2VkN2I0NTIwOWNkNDhlMDc2MzkyY2JiYiIsIjhjN2ZhZDk3MmEwZTQwMDNiNjMwOTU2MjY4NjQ0OTAzIiwiNTYzMzk4ODU3YjI4NGQxNGE0ODU3NWUwNjk5MGI5ZTQiLCJwcm8iLCJmMjA3Y2E2MGVjMDY0ZWRiYmNiYzI2OTk3OTg1NDAwYSIsIjg5NWYxMDE1YTIxNzQxYmI5NzAxOWE5MjhjMmM1NzhiIiwiZjNlZWZkMDQzY2Y2NGI5NmEwMzEwZTU5MjVjNjRmMjgiXX0.O-lQmvugXGR3Ea15odoV28Z2bp_CjX6sWinD8fx_ll5HWKiwZdIZeYWwk34SJ_0Tkq5M1Ov-zBT77ilxaQSEyguD8yhgQ_QuwYsnnabGtXKTXETc3LrSsWZkvnVgMd1Y5UKVs7akKvFDjcIN_bROauLnyPFoxEJpW88xEGhLdXo
b3
fbfeec50d5954441b63c0204dee50c68-fc2fb32786ac0f05-1
cache-control
max-age=0
origin
https://workspace.zhihuiya.com
priority
u=1, i
referer
https://workspace.zhihuiya.com/
sec-ch-ua
"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"Windows"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-site
user-agent
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0
vary
Accept-Language,Authorization,x-api-version
x-api-version
2.0
x-device-id
75a24e70-3236-11f1-9806-0519894c2bf7
x-p-s
cf186c2f60eafb0ac2a1f5726c58d18e2e8938462b2eb00f49e2ead967a63695
x-patsnap-from
w-analytics-workspace
x-requested-with
XMLHttpRequest
x-site-lang
CN
x-t
1775792182451
```

3. 
我找到了摘要的文字获取POST,但是有另外一个十分相似的POST和他一起出现???
第一个patent请求
```md
请求 URL
https://search-service.zhihuiya.com/core-search-api/search/translate/patent
请求方法
POST
状态代码
200 OK
Remote Address
81.70.127.178:443
引用站点策略
strict-origin-when-cross-origin
access-control-allow-credentials
true
access-control-allow-origin
https://analytics.zhihuiya.com
access-control-expose-headers
content-disposition
content-encoding
gzip
content-type
application/json;charset=utf-8
date
Fri, 10 Apr 2026 03:46:43 GMT
set-cookie
tgw_l7_route=f867098e173da53233789f8c2d2640c9; Expires=Fri, 10-Apr-2026 03:47:13 GMT; Path=/; sameSite=None; Secure
vary
Origin
vary
Access-Control-Request-Method
vary
Access-Control-Request-Headers
vary
Accept-Encoding, User-Agent
via
kong/0.14.1
x-client-id
f58bbdfdd63549dbb64fed4b816c8bfc
x-correlation-id
874e3432-2de3-4ff1-9152-7e8d758b173f
x-kong-proxy-latency
7
x-kong-upstream-latency
18
:authority
search-service.zhihuiya.com
:method
POST
:path
/core-search-api/search/translate/patent
:scheme
https
accept
application/json, text/plain, */*
accept-encoding
gzip, deflate, br, zstd
accept-language
zh-CN,zh;q=0.9,ja;q=0.8,en-US;q=0.7,en-IN;q=0.6,en;q=0.5,ru;q=0.4,en-GB;q=0.3,bn-IN;q=0.2,bn;q=0.1
authorization
Bearer eyJhbGciOiJSUzI1NiJ9.eyJqdGkiOiIyZDIzNzhhNi1iNTIwLTRiMTAtYjM4Zi1iMTYwNzhmNjFmMzYiLCJpc3MiOiJwYXRzbmFwIiwic3ViIjoiZWZhYTI4YzUwZWRlNGRlNjhlMjkyNmU2NmFlMTc1ZGIiLCJpYXQiOjE3NzU3OTE3NTUsImV4cCI6MTc3NTc5MzU1NSwidGVuYW50X2lkIjoiYTgwNzMwMDEzYTI0NGRkMDhmMTc1ZTI1YTRkM2E4ODIiLCJwcm9kdWN0IjoicHJvIiwidXNlcl9pZCI6ImVmYWEyOGM1MGVkZTRkZTY4ZTI5MjZlNjZhZTE3NWRiIiwic2Vzc2lvbiI6IjUzYjNlYTdmLTZhY2YtNDcwMy05YjAwLWZjOWQ1ZDgzYTBhMSIsImNsaWVudF9pZCI6ImY1OGJiZGZkZDYzNTQ5ZGJiNjRmZWQ0YjgxNmM4YmZjIiwiYXV0aG9yaXRpZXMiOlsiNDQzMDIiLCIxeWV5IiwiMzFjOCIsIjM1enUiLCJ0MDAwOCIsImEwNnEiLCI0MDEwMCIsIjQyMDAwIiwiN2o2NiIsImdxd2ciLCIzYXB0IiwiNDA1MDAiLCIxd3poIiwiNDA1MDYiLCJ0MDAwMyIsIjM2dGciLCIzY2RqIiwiNDA5MDAiLCI0MjgwMCIsIjQwNTAzIiwiODAwMDMiLCJzdnR1IiwiODAwMDEiLCI1YjJvIiwiODAwMDciLCIzYmM2IiwiM3NtMiIsIjd1Y2kiLCJiMDAwMyIsIjN4bzAiLCIzcHk0IiwiMjAxMDAiLCI0NTEwMSIsIjNiY2UiLCIzeXB6IiwiNDM2MDEiLCI2MDA2YyIsIjQzMjA2IiwiMjAxMDYiLCIzY2VrIiwiY29nNyIsIjMxbDMiLCIxcG4wIiwiMXdyeiIsIjE4Zm4iLCIzY3VmIiwiM3BucyIsIjM4cHAiLCI2MDBoYyIsIjQyMTAyIiwiMWp0MCIsIjQyNTAwIiwiM2M1YSIsIjQ0MDAwIiwiM3l6ZCIsIjFwbmwiLCI0MjUwNyIsIjQyOTAzIiwibjAwMDEiLCI2MDA3YyIsIjdqNnEiLCIzYXQzIiwiMzEzNSIsIjExYzEiLCIxcGc2IiwiMXcxbSIsIjMxY3EiLCI2MDBpYyIsIjYwMGpjIiwicWViYiIsIjFjZWkiLCIzYWNvIiwiN3FxMCIsIjQxMDA0IiwiMzBzZyIsIjFqYnkiLCI0MTAwMSIsIjQxODAwIiwiNDEwMDciLCI4MDAwOSIsIjIzMzE1IiwiNjAwOGMiLCI0MjYxNCIsIjgwMDE0IiwiMThyMSIsIjMzcjMiLCIzMTNkIiwiNjAwYmMiLCIzMDFiIiwiMzJoNyIsImMwY20iLCIxd3RxIiwiMzZ4OSIsIjNjZnoiLCIzcHI5IiwiMWoxYiIsIjMxdWEiLCIzMGw4IiwiMTZkYzQ4YjY5OTUzNGQ4NGI5YTgxMmMyZWQwZTA3M2QiLCIxcGZvIiwiMjE1MDEiLCI0MjIwMyIsIjQyMzI0IiwiNDY0MDEiLCIxdzRsIiwibW5kNyIsIjYwMDFjIiwiNDI2MDQiLCIxam4xIiwiNDA3MDQiLCIxOHJlIiwiNDA3MDEiLCIxNWNmIiwiODAyMDAiLCIzcDhlIiwiNDE5MDUiLCIzeGFoIiwiMTFjZSIsIjNieDciLCIzdm15IiwiM3BpbCIsImNvdXJzZV9wdWJsaWNfZGFjYmJhMTJmYWZjMWQyNjVmYjlmZTFhNTc3NGRmOTQiLCIxMWUyIiwiNW1tdyIsIjF5aWYiLCI0MzAwMyIsIjIwMzAwIiwiNDIzMTMiLCIzMmI1IiwiNDExMDAiLCIxdGo5IiwiMzFnZiIsIjF3ZnUiLCI0MjMxNSIsIjIwNzAwIiwiMXdoOCIsIjNnMTQiLCI0MDgxMSIsIjQwNDA5IiwiMThybiIsIjFqMnkiLCIxamRrIiwiNDA4MDgiLCIzajVhIiwiMzBuZyIsIjIwMTEzIiwiM202NiIsIjQ0NjAxIiwiM2NibiIsIjFncGwiLCIxeTF6IiwiMzN2NCIsIm16bHgiLCI0MDQwMSIsIjMxODYiLCI0MDQwNyIsInN5eW4iLCI0MjcwMCIsIjM2em4iLCI0MDQwNCIsIjQwODAwIiwiYTA1YyIsIjQzMTAyIiwiMjAwMDQiLCIyMDQwMCIsIjc5bWUiLCI0MzUwMSIsIjIyNzA1IiwiMjAwMDAiLCI0MDUxMyIsIjQzOTAzIiwiNDE2MDAiLCI0MDUxMCIsIjIwODAxIiwiN2o1OCIsIjIwMDA4IiwiMjAwMDYiLCIxd2hqIiwiMTE0eiIsIjMyYmkiLCIzOHA0IiwiZDAwMDEiLCIzMmJoIiwiNjA1MDIiLCJkMDAwMCIsIjNjMW0iLCIzY3NxIiwiMXlkayJdLCJwcm9kdWN0cyI6WyJjb3BpbG90IiwiY2hlbWljYWwiLCJlYzRiZGY5Yjc2YTk0YTgzYWRlNWMwNjIyYzM0NjA2MiIsImMxMDgzMjM0OWY4NzRjOGZhYmQwZTljYTc0YTJkOTJlIiwiYmFlOTEzNzdlZDdiNDUyMDljZDQ4ZTA3NjM5MmNiYmIiLCI4YzdmYWQ5NzJhMGU0MDAzYjYzMDk1NjI2ODY0NDkwMyIsIjU2MzM5ODg1N2IyODRkMTRhNDg1NzVlMDY5OTBiOWU0IiwicHJvIiwiZjIwN2NhNjBlYzA2NGVkYmJjYmMyNjk5Nzk4NTQwMGEiLCI4OTVmMTAxNWEyMTc0MWJiOTcwMTlhOTI4YzJjNTc4YiIsImYzZWVmZDA0M2NmNjRiOTZhMDMxMGU1OTI1YzY0ZjI4Il19.ndqiD1czmsGeYdXJ7l25pV5mQx-ylExNiapwfMG00_T77GYAagPETPXZMmMqq6kmG_b5252SYo7igy71HAljNsi8GuNaGmnXiAtjwHMxKzSudgl1or_PP4EfCg648hNg9hepKNE2ie1vCLczlkF3MmX15iGOEeEtX07qjH_TjRM
b3
c7ff33fb0f4247d79eb63464447067a0-27bb5bf25103a041-1
content-length
620
content-type
application/json
origin
https://analytics.zhihuiya.com
priority
u=1, i
referer
https://analytics.zhihuiya.com/
sec-ch-ua
"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"Windows"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-site
user-agent
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0
x-api-version
2.0
x-device-id
75a24e70-3236-11f1-9806-0519894c2bf7
x-p-s
4b0e20ed2a605ed85201d6e170ee8357e7b56cc9110141bed57d4a0354aad807
x-patsnap-from
w-analytics-patent-view
x-requested-with
XMLHttpRequest
x-site-lang
CN
x-t
1775792802605
```

请求负载
```md
{
    "patent_id": "a4979582-5335-42bb-bc82-cf6519e7c210",
    "highlight": true,
    "lang": "CN",
    "original": false,
    "field": "TITLE",
    "source_type": "workspace",
    "view_type": "workspace",
    "bio_uk": "",
    "uk": "undefined",
    "ws_view_type": "tablelist",
    "page": 1,
    "_type": "workspace",
    "workspace_id": "ccb6031b05034c7ab2c4b120c2dc3155",
    "sort": "wtasc",
    "rows": "20",
    "folder_id": "da49b4d09d784eb7a43790c17611b861",
    "qid": "",
    "efqid": "",
    "cond": "",
    "product": "Analytics",
    "path": "",
    "signature": "SlyJYZh8rcYm7FkbmyfSEbN7DmQefitqdIkhrtBXiFM=",
    "shareFrom": "VIEW",
    "date": "20260410T034642Z",
    "expire": "94608000",
    "shareId": "FGBB71D62FEF8EF82F7238F08BF528EC",
    "version": "1.0"
}
```

第二个patent请求(能够获得正确的摘要文字信息)
```md
请求 URL
https://search-service.zhihuiya.com/core-search-api/search/translate/patent
请求方法
POST
状态代码
200 OK
Remote Address
81.70.127.178:443
引用站点策略
strict-origin-when-cross-origin
access-control-allow-credentials
true
access-control-allow-origin
https://analytics.zhihuiya.com
access-control-expose-headers
content-disposition
content-encoding
gzip
content-type
application/json;charset=utf-8
date
Fri, 10 Apr 2026 03:46:43 GMT
set-cookie
tgw_l7_route=8dc9c6704c920018fb85f49c343d25c7; Expires=Fri, 10-Apr-2026 03:47:13 GMT; Path=/; sameSite=None; Secure
vary
Origin
vary
Access-Control-Request-Method
vary
Access-Control-Request-Headers
vary
Accept-Encoding, User-Agent
via
kong/0.14.1
x-client-id
f58bbdfdd63549dbb64fed4b816c8bfc
x-correlation-id
b152a9ed-69e6-4444-92b3-017420f60aeb
x-kong-proxy-latency
22
x-kong-upstream-latency
214
:authority
search-service.zhihuiya.com
:method
POST
:path
/core-search-api/search/translate/patent
:scheme
https
accept
application/json, text/plain, */*
accept-encoding
gzip, deflate, br, zstd
accept-language
zh-CN,zh;q=0.9,ja;q=0.8,en-US;q=0.7,en-IN;q=0.6,en;q=0.5,ru;q=0.4,en-GB;q=0.3,bn-IN;q=0.2,bn;q=0.1
authorization
Bearer eyJhbGciOiJSUzI1NiJ9.eyJqdGkiOiIyZDIzNzhhNi1iNTIwLTRiMTAtYjM4Zi1iMTYwNzhmNjFmMzYiLCJpc3MiOiJwYXRzbmFwIiwic3ViIjoiZWZhYTI4YzUwZWRlNGRlNjhlMjkyNmU2NmFlMTc1ZGIiLCJpYXQiOjE3NzU3OTE3NTUsImV4cCI6MTc3NTc5MzU1NSwidGVuYW50X2lkIjoiYTgwNzMwMDEzYTI0NGRkMDhmMTc1ZTI1YTRkM2E4ODIiLCJwcm9kdWN0IjoicHJvIiwidXNlcl9pZCI6ImVmYWEyOGM1MGVkZTRkZTY4ZTI5MjZlNjZhZTE3NWRiIiwic2Vzc2lvbiI6IjUzYjNlYTdmLTZhY2YtNDcwMy05YjAwLWZjOWQ1ZDgzYTBhMSIsImNsaWVudF9pZCI6ImY1OGJiZGZkZDYzNTQ5ZGJiNjRmZWQ0YjgxNmM4YmZjIiwiYXV0aG9yaXRpZXMiOlsiNDQzMDIiLCIxeWV5IiwiMzFjOCIsIjM1enUiLCJ0MDAwOCIsImEwNnEiLCI0MDEwMCIsIjQyMDAwIiwiN2o2NiIsImdxd2ciLCIzYXB0IiwiNDA1MDAiLCIxd3poIiwiNDA1MDYiLCJ0MDAwMyIsIjM2dGciLCIzY2RqIiwiNDA5MDAiLCI0MjgwMCIsIjQwNTAzIiwiODAwMDMiLCJzdnR1IiwiODAwMDEiLCI1YjJvIiwiODAwMDciLCIzYmM2IiwiM3NtMiIsIjd1Y2kiLCJiMDAwMyIsIjN4bzAiLCIzcHk0IiwiMjAxMDAiLCI0NTEwMSIsIjNiY2UiLCIzeXB6IiwiNDM2MDEiLCI2MDA2YyIsIjQzMjA2IiwiMjAxMDYiLCIzY2VrIiwiY29nNyIsIjMxbDMiLCIxcG4wIiwiMXdyeiIsIjE4Zm4iLCIzY3VmIiwiM3BucyIsIjM4cHAiLCI2MDBoYyIsIjQyMTAyIiwiMWp0MCIsIjQyNTAwIiwiM2M1YSIsIjQ0MDAwIiwiM3l6ZCIsIjFwbmwiLCI0MjUwNyIsIjQyOTAzIiwibjAwMDEiLCI2MDA3YyIsIjdqNnEiLCIzYXQzIiwiMzEzNSIsIjExYzEiLCIxcGc2IiwiMXcxbSIsIjMxY3EiLCI2MDBpYyIsIjYwMGpjIiwicWViYiIsIjFjZWkiLCIzYWNvIiwiN3FxMCIsIjQxMDA0IiwiMzBzZyIsIjFqYnkiLCI0MTAwMSIsIjQxODAwIiwiNDEwMDciLCI4MDAwOSIsIjIzMzE1IiwiNjAwOGMiLCI0MjYxNCIsIjgwMDE0IiwiMThyMSIsIjMzcjMiLCIzMTNkIiwiNjAwYmMiLCIzMDFiIiwiMzJoNyIsImMwY20iLCIxd3RxIiwiMzZ4OSIsIjNjZnoiLCIzcHI5IiwiMWoxYiIsIjMxdWEiLCIzMGw4IiwiMTZkYzQ4YjY5OTUzNGQ4NGI5YTgxMmMyZWQwZTA3M2QiLCIxcGZvIiwiMjE1MDEiLCI0MjIwMyIsIjQyMzI0IiwiNDY0MDEiLCIxdzRsIiwibW5kNyIsIjYwMDFjIiwiNDI2MDQiLCIxam4xIiwiNDA3MDQiLCIxOHJlIiwiNDA3MDEiLCIxNWNmIiwiODAyMDAiLCIzcDhlIiwiNDE5MDUiLCIzeGFoIiwiMTFjZSIsIjNieDciLCIzdm15IiwiM3BpbCIsImNvdXJzZV9wdWJsaWNfZGFjYmJhMTJmYWZjMWQyNjVmYjlmZTFhNTc3NGRmOTQiLCIxMWUyIiwiNW1tdyIsIjF5aWYiLCI0MzAwMyIsIjIwMzAwIiwiNDIzMTMiLCIzMmI1IiwiNDExMDAiLCIxdGo5IiwiMzFnZiIsIjF3ZnUiLCI0MjMxNSIsIjIwNzAwIiwiMXdoOCIsIjNnMTQiLCI0MDgxMSIsIjQwNDA5IiwiMThybiIsIjFqMnkiLCIxamRrIiwiNDA4MDgiLCIzajVhIiwiMzBuZyIsIjIwMTEzIiwiM202NiIsIjQ0NjAxIiwiM2NibiIsIjFncGwiLCIxeTF6IiwiMzN2NCIsIm16bHgiLCI0MDQwMSIsIjMxODYiLCI0MDQwNyIsInN5eW4iLCI0MjcwMCIsIjM2em4iLCI0MDQwNCIsIjQwODAwIiwiYTA1YyIsIjQzMTAyIiwiMjAwMDQiLCIyMDQwMCIsIjc5bWUiLCI0MzUwMSIsIjIyNzA1IiwiMjAwMDAiLCI0MDUxMyIsIjQzOTAzIiwiNDE2MDAiLCI0MDUxMCIsIjIwODAxIiwiN2o1OCIsIjIwMDA4IiwiMjAwMDYiLCIxd2hqIiwiMTE0eiIsIjMyYmkiLCIzOHA0IiwiZDAwMDEiLCIzMmJoIiwiNjA1MDIiLCJkMDAwMCIsIjNjMW0iLCIzY3NxIiwiMXlkayJdLCJwcm9kdWN0cyI6WyJjb3BpbG90IiwiY2hlbWljYWwiLCJlYzRiZGY5Yjc2YTk0YTgzYWRlNWMwNjIyYzM0NjA2MiIsImMxMDgzMjM0OWY4NzRjOGZhYmQwZTljYTc0YTJkOTJlIiwiYmFlOTEzNzdlZDdiNDUyMDljZDQ4ZTA3NjM5MmNiYmIiLCI4YzdmYWQ5NzJhMGU0MDAzYjYzMDk1NjI2ODY0NDkwMyIsIjU2MzM5ODg1N2IyODRkMTRhNDg1NzVlMDY5OTBiOWU0IiwicHJvIiwiZjIwN2NhNjBlYzA2NGVkYmJjYmMyNjk5Nzk4NTQwMGEiLCI4OTVmMTAxNWEyMTc0MWJiOTcwMTlhOTI4YzJjNTc4YiIsImYzZWVmZDA0M2NmNjRiOTZhMDMxMGU1OTI1YzY0ZjI4Il19.ndqiD1czmsGeYdXJ7l25pV5mQx-ylExNiapwfMG00_T77GYAagPETPXZMmMqq6kmG_b5252SYo7igy71HAljNsi8GuNaGmnXiAtjwHMxKzSudgl1or_PP4EfCg648hNg9hepKNE2ie1vCLczlkF3MmX15iGOEeEtX07qjH_TjRM
b3
3841f6a069d74f7aa7eea9b4d2fcac5e-e545ffe4939ed89e-1
content-length
619
content-type
application/json
origin
https://analytics.zhihuiya.com
priority
u=1, i
referer
https://analytics.zhihuiya.com/
sec-ch-ua
"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"Windows"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-site
user-agent
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0
x-api-version
2.0
x-device-id
75a24e70-3236-11f1-9806-0519894c2bf7
x-p-s
4b0e20ed2a605ed85201d6e170ee8357e7b56cc9110141bed57d4a0354aad807
x-patsnap-from
w-analytics-patent-view
x-requested-with
XMLHttpRequest
x-site-lang
CN
x-t
1775792802605
```

请求负载
```md

{
    "patent_id": "a4979582-5335-42bb-bc82-cf6519e7c210",
    "highlight": true,
    "lang": "CN",
    "original": false,
    "field": "ABST",
    "source_type": "workspace",
    "view_type": "workspace",
    "bio_uk": "",
    "uk": "undefined",
    "ws_view_type": "tablelist",
    "page": 1,
    "_type": "workspace",
    "workspace_id": "ccb6031b05034c7ab2c4b120c2dc3155",
    "sort": "wtasc",
    "rows": "20",
    "folder_id": "da49b4d09d784eb7a43790c17611b861",
    "qid": "",
    "efqid": "",
    "cond": "",
    "product": "Analytics",
    "path": "",
    "signature": "SlyJYZh8rcYm7FkbmyfSEbN7DmQefitqdIkhrtBXiFM=",
    "shareFrom": "VIEW",
    "date": "20260410T034642Z",
    "expire": "94608000",
    "shareId": "FGBB71D62FEF8EF82F7238F08BF528EC",
    "version": "1.0"
}
```


至此,所有的信息都被解锁了.


4. 
主要竞争对手	发明创造名称	申请人/专利权人	发明人	申请号/专利号	申请日期	授权日期	法律状态	技术方案

接下来我要你做一个新的流程文件.流程文件内容:调用表格生成模块.表格生成模块内容:传入一个日期,是xxxx-xx年月结构,然后生成一个excel表格.表格结构是:

标题(合并单元格,内容一定是"竞争对手专利情报(xxxx年x月)")
序号  主要竞争对手	发明创造名称	申请人/专利权人	发明人	申请号/专利号	申请日期	授权日期	法律状态	技术方案

其中标题那个单元格,宽度囊括上述所有的字段
序号主要是按专利排的,每一条具体的专利需要对应一个序号
主要竞争对手那个格子也有合并单元格的要求,如果不同主要竞争对手相同,那么合并单元格

法律状态根据数据中的LEGAL_STATUS字段,经过zhy\data\tmp\mid1.json中的映射,映射成中文.如果映射不到,显示警告,并不要在表格中输出内容

技术方案那里填摘要即可

授权日期,如果一条专利没有授权日期,就填"/",否则填写授权日期.

摘要信息和授权日期信息都在补充信息文件夹中,就是你刚刚写的那些

还有什么关键信息我需要补充的么

5. 
表格所有单元格都要在四周画边框;所有表格表头那里,字段名称要加粗;表格标题加粗

6. 
很好，接下来就是根据已经抓取下来的专利内容，获取补充信息（授权日期和摘要）
这个或许可以直接参考现在有的模块？你怎么看