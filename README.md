# Personal Calendar

自己维护的中国大陆节假日、调休、常见节日与二十四节气订阅。

## 当前状态：原生班休角标兼容性验证

当前只发布 4 条测试事件，尚未完成完整日历或年度自动抓取。
在用户的 iPhone 18 Pro Max / iOS 27 / 香港地区下，原生角标和同一 URL
刷新均通过后，才继续完整建设。CI 成功不代表 Apple 实机验收通过。

- 测试说明：https://shiki1255.github.io/personal-calendar/
- HTTPS 订阅：https://shiki1255.github.io/personal-calendar/compatibility/apple-badges.ics
- Apple 添加：日历 → 日历 → 添加日历 → 添加订阅日历 → 粘贴 HTTPS 地址。
- 保留香港地区，暂时隐藏其他节日日历，检查 2026-10-07 为“休”、10-10 为“班”，
  10-09 和 10-11 无角标。标题文字不算角标。
- 在原任务聊天反馈。首轮通过后发布 r2：保留原订阅，10-09 的 r1 应变为 r2，
  事件总数仍是 4。不能通过重新导入/重新订阅来冒充刷新成功。

Apple 扩展为兼容性候选，未保证跨地区和所有系统版本的行为。若目标设备不支持，
暂停完整建设，不自动改地区或用标题模拟通过。

## 两种正式订阅模式（待实机验证通过后建设）

| 模式 | 文件 | 使用方式 |
|---|---|---|
| 整合 | calendar.ics | 一条订阅包含全部内容，内部合并重复事件 |
| 分类 | holidays.ics | 官方调休及原生班休角标 |
| 分类 | festivals.ics | 常见传统、国际节日和圣周 |
| 分类 | solar_terms.ics | 二十四节气 |

分类可选一个、多个或全部，分别显示/隐藏和选颜色。推荐整合版或分类组合二选一；
不要依赖客户端在多个订阅之间去重。切换时取消旧订阅再添加新订阅。
正式地址预留于站点根目录，目前不提供空白文件伪装成完整订阅。

## 数据来源和边界

测试日期来自国务院办公厅《2026年部分节假日安排的通知》，国办发明电〔2025〕7号，
2025-11-04 发布。中国政府网首选页面访问失败后，使用北京市政府正式转载。
data/compatibility 保存纯文本公告正文、来源、获取时间及 SHA-256；不运行来源网页脚本。
不使用其他人的 ICS、日历成品或私人 API。

## 本地验证和构建

Python 3.12。生成器仅使用标准库；测试使用锁定的独立 icalendar 解析器。
本机 shell 使用 PowerShell 7。测试依赖安装到项目专用虚拟环境，不改系统 Python：

```powershell
python -m venv D:/CodexProjects/codex_runtime/personal-calendar/compat-venv
& D:/CodexProjects/codex_runtime/personal-calendar/compat-venv/Scripts/python.exe -m pip install --require-hashes -r requirements-test.txt
python -B scripts/preflight.py
& D:/CodexProjects/codex_runtime/personal-calendar/compat-venv/Scripts/python.exe -B -m unittest discover -s tests -v
python -B scripts/build_compat.py --output D:/CodexProjects/codex_workbench/projects/personal-calendar/outputs/compatibility-r1
```

输出拒绝写入源码仓库。CI 使用 RUNNER_TEMP，校验通过后显式发布 Pages。
目前只配置 push / pull_request / workflow_dispatch，不配置定时抓取。
测试覆盖来源哈希、准确日期、Apple 字段、全天结束日期、UTF-8 折行、转义、稳定 UID、
重复生成、r1→r2 只修订一个事件及防止发布不完整正式源。

## 治理与许可

本仓库包含自有身份清单、任务预检和操作规则；已只读参考治理根的当前规则。
未修改或声称登记到中央仓库注册表，源码和运行不依赖兄弟仓库。
生成产物与测试虚拟环境分别放在 workbench 与 runtime，未启用自动清理。
代码 MIT；政府原文注明来源，不声明归本项目所有。完整后续规格见 docs/design.md。
