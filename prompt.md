

main(要爬取的内容)

如果无法直接进入首页（cookie过期）{
    重新登录
    从leap跳转到专家分析页面
    从专家分析页面筛选条件
    寻找
}

将getdata1中的
```python
    page.get_by_role("tab", name="地区", exact=True).click()
    wait_before_action(page)
    page.get_by_role("tab", name="北美").click()
    wait_before_action(page)
    page.get_by_role("checkbox", name="北美 (all)").click()
    wait_before_action(page)
    page.get_by_role("tab", name="品类").click()
    wait_before_action(page)
    page.get_by_role("tab", name="美容与个人护理").click()
    wait_before_action(page)
    page.get_by_role("checkbox", name="头发护理").click()
    wait_before_action(page)
    page.get_by_role("checkbox", name="面部护肤品").click()
    wait_before_action(page)
    page.get_by_role("button", name="Open dropdown").click()
    wait_before_action(page)
    page.get_by_role("link", name="您的GNPD中心 从这里开启您的GNPD").click()
    wait_before_action(page)
    page.goto("https://clients.mintel.com/gnpd-hub")
    wait_before_action(page)
    page.locator("#category-select").get_by_role("img").click()
    wait_before_action(page)
    page.get_by_role("option", name="面部/颈部护理").click()
    wait_before_action(page)
    page.get_by_role("button", name="应用筛选项").click()
    wait_before_action(page)
    with page.expect_popup() as page1_info:
        page.get_by_role("link", name="在GNPD中查看更多产品").click()
    page1 = page1_info.value
    wait_before_action(page1)
```

这一部分改装成一个模块，职责就是：从专家页面跳转到产品列表页面。


- 阅读根目录test.html,说说你看到了什么?

- 参考现有的modules中与名字搜索相关的模块,实现以下模块:
1.新增列表选项中,提取所有选项的产品名称(注意是"新增",这可能需要getdata1维护一个集合)
2.向下滚动到页面底部,等待,直至新列表选项出现(这个可能需要斟酌一下,程序怎么知道这个新列表有没有被加载出来)
3.选中列表选项(就是每一个列表选项都有一个小方块,在html看到了吧?点击一下将其切换为选中状态)
4.下载已经选中的选项(这个需要我后续提供示例代码,你不知道也没关系)
先说说你的方案或者疑问?


- 将main给改成:

调用 进入产品列表页面（登录-》专家分析-》产品列表页面） 模块

循环次数=n
名称列表=m(也就是用户要查询的)

循环 遍历名称列表{
    name=名称
    调用 精确搜索 模块

    页面搜索模块（name）{
        循环 n次{
            调用 新增列表选项中,提取所有选项的产品名称 模块（如果是第一次调用，要求这个模块会直接出来初始列表内容）
            如果某个产品和m名称一模一样{
                直接下载对应内容
                return
            }
            向下滚动到页面底部,等待,直至新列表选项出现
        }
        日志：进行n次搜索页扩展后仍然没有找到符合的内容，请检查名字是否正确
    }
    删除当前精确搜索条件
}

输出选中情况:m中有哪些没有找到,有哪些找到了.