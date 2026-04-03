编写一个新任务：完成三个步骤。
- 执行tyc\tasks\risk_2_async_task.py的任务得出公司数据
- 执行tyc\tasks\risk_daily_convert_task.py的任务将公司数据惊醒格式重拍与筛选
- 执行tyc\tasks\risk_daily_upload_task.py的任务将公司数据上传到数据库
但是各个tasks之间不能相互依赖，所以这些模块需要重新拼装