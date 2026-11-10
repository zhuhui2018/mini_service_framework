# mini_service_framework

一个最小可用的任务编排框架：按时间触发任务 → 任务失败就重试 → 按结果走不同分支 → 最后出报告并停止。

## 分层（依赖只能从上往下）

```
main.py              入口层    装配对象、启动、等待结束
├── framework/
│   ├── service.py   编排层    谁跑完了、下一步派谁（分支 / 告警 / 停止）
│   ├── tasks/       任务层    每个任务只管自己怎么干活（run）
│   ├── core/        核心层    注册表 / 调度器 / 执行器 / 重试 / 触发器 / 工厂
│   ├── support/     支撑层    校验器 / 分支定义 / 去重 / 规则（无状态小工具）
│   └── plugins/     插件层    pytest 结果收集器（靠 hook 被调用）
├── config.yaml      配置层    路径、间隔等可变量（横切各层）
├── tests/           用例层    框架自身的单元测试（62 条）
└── legacy/          历史文件  YAML 版 main、TaskFactory 草稿、Queue 实验（不参与运行）
```

三条依赖规则：

1. `core/` 不认识任何具体任务，只认识"有 name 和 run() 的对象"——所以加任务不用改它。
2. `tasks/` 不认识 `service`，只依赖 `core` 的接口。
3. 改配置不动代码，加任务不改框架。

## 安装与运行

```bash
cd mini_service_framework
python3 -m venv .venv            # 已有 .venv 可跳过
.venv/bin/python -m pip install -r requirements.txt

.venv/bin/python -m pytest       # 跑框架自身的用例（应为 62 passed）
.venv/bin/python main.py         # 跑框架本体
```

## 用例清单（tests/）

| 文件                          | 测什么                              | 条数 |
| --------------------------- | -------------------------------- | -- |
| test\_registry.py           | 注册 / 取名 / 同名覆盖                   | 4  |
| test\_retry\_policy.py      | 重试边界（差一问题）                       | 6  |
| test\_executor.py           | 执行成功 / 重试后成功 / 重试耗尽              | 4  |
| test\_task\_factory.py      | 多余参数被过滤、缺参数报错                    | 4  |
| test\_validate.py           | 五类校验器 + 目录不存在的防御                 | 8  |
| test\_scheduler.py          | 同名去重、成功后不再入队、回调顺序                | 6  |
| test\_result\_recorder.py   | 记录顺序与引用语义                        | 3  |
| test\_pytest\_collector.py  | 只统计 call 阶段                      | 6  |
| test\_log\_archive\_task.py | 首次归档 / 重试模式 / 搬运失败 / 空目录         | 5  |
| test\_pytest\_task.py       | nodeid 拼装 / 指定用例 / 重试模式 / 目录不存在  | 8  |
| test\_report\_task.py       | 报告输出内容与 terminal 标记              | 3  |
| test\_service\_routing.py   | 失败派重试 / 成功派报告 / terminal 停止 / 链断 | 5  |

### **目前跑用例时存在的7个问题，待解决**

1. **编排线程会崩**：`service.py` 第 79 行 `if task.retryable` 写死假设，结果列表里一旦出现 `ReportTask` 之类没有 `retryable` 属性的任务，就 `AttributeError`，分支逻辑整条静默失效。  
   证据：`main.py` 实跑输出 `AttributeError: 'ReportTask' object has no attribute 'retryable'`。
2. **重试链会断**：分支匹配用 `startswith("failed_retry")`，但实际生成的名字是 `PytestTask_retry_2`，两个条件都不满足 → 重试失败后再也不派任务，而 `is_running` 仍为 True，`main.py` 的等待循环永远转（卡死）。  
   用例：`test_service_routing.py::test_retry_chain_stalls_and_never_stops`
3. **告警分支几乎不可达**：`failure_counts` 按 `task_name` 计数，而每次重试都换新名字，计数永远是 1，到不了 `max_retries`。
4. **重试次数差一**：`max_retry_count=3` 实际只跑 3 次（1 次首发 + 2 次重试），不是"重试 3 次"。要么改判定，要么改名 `max_attempts`。
5. **目录不存在返回 None**：`PytestTask.run()` 在 test\_dir 不存在时 `return`（None），调度器把 None 记进结果，后续 `.get()` 直接崩。应返回结构化失败结果。
6. **空目录会跑全仓库**：扫不到用例时 `nodeids` 为空，`pytest.main(["-q"])` 不指定目标 → pytest 去跑当前工作目录下的所有用例。应在 nodeids 为空时直接返回"无用例"。
7. **归档只扫一层**：`LogArchiveTask` 对 `log_dirs` 只 `os.listdir` 一层，而实际日志在 `app1/`、`app2/` 子目录里 → 归档 0 个文件，却判成功，然后触发报告、误停整个服务。

## 待优化的 9 项

| 序号 | 任务            | 产出                                                | 验收标准                                           |
| -- | ------------- | ------------------------------------------------- | ---------------------------------------------- |
| 1  | 抽象基类 BaseTask | 所有任务继承基类，强制实现 run()                               | 新增任务时自动继承接口，无需手动检查                             |
| 2  | 装饰器自动注册任务     | 去掉 main.py 中手动 register_task                     | 任务类定义时自动注册到 Registry                           |
| 3  | 上下文管理器管理资源    | LogArchiveTask 等用 with 替代手动 close                 | 文件句柄不会泄漏                                       |
| 4  | 策略模式处理分支条件    | 把 condition 字典换成策略类                               | 新增条件类型时不需要修改 _check_and_trigger_downstream |
| 5  | 工厂模式创建任务实例    | 用 TaskFactory 替代直接调用类                             | 新增任务类型时不需要修改调用方代码                              |
| 5  | 高阶函数优化遍历逻辑    | 用 filter/map 简化 _check_and_trigger_downstream | 方法体从 40 行压缩到 15 行以内                            |
| 7  | YAML 配置扩展     | 任务、触发器、分支全部由 YAML 驱动                              | main.py 只负责加载 YAML 和启动                         |
| 8  | 分支链去重优化       | 支持多个 BranchChain 并行，匹配任意 upstream_name           | 添加新 BranchChain 不需要改框架代码                       |
| 9  | 下游结束逻辑区分      | 报告任务完成后停止轮询，重试任务继续                                | 报告生成后程序能正常退出                                   |

### 原始学习笔记

一，在实际完成框架过程中遇到的问题和学习感悟

1)不知道最小处理流程，每个类需要干什么  
2)不知道init初始化的时候，参数是应该传进去还是自定义  
3)我有个问题是一个类对象A被当成参数传递给另一个类B的init初始化中，我刚开始搞不明白都没有实例化，  
为什么类B中的self.a = a对象后，self.a能用A这个类的方法，后来我才理解python的运行机制是这样  
的，self.a.xx() 之所以能写，不是因为 Python 已经知道 self.a 是 类A 实例。  
而是因为 Python 允许你先写下来，等运行时再决定它到底是不是。

4)我不知道哪些类中是要自己new一个类，哪些是可以直接通过参数传递过来的，所以要训练 看清“一个对象是从哪里来的 → 被谁拿着 → 被谁传给谁”  
5）写这个框架的过程中，其实我已经知道了这个流程，但是涉及到流程中的每个模块该负责什么的时候，我还是不知道，脑子是乱的，然后我发现一个训练方法特别管用  
a.这一行是谁负责的  
比如：  
“判断条件” → Trigger  
“执行任务” → Task  
b.这个模块不应该干什么  
比如：  
Trigger ❌不执行任务  
Scheduler ❌ 不判断条件  
c.没有这个模块，会怎么样  
比如：  
没 Scheduler → 任务乱执行  
没 Registry → 找不到 Task  
6）一定要知道自己所做的这个框架的最少必要知识有哪些，比如我这个框架最小必要知识就是最小骨架，只把每个类的职责弄清楚和状态流转完成一个最小的框架，本来我是刚开始打算做一个大的框架的，包括所有功能和高级特性，但一圈实践下来发现挺困难的，所以我改变策略，只做最小必要，然后多做一些，果然，等第3个的时候明显有感觉了，然后再补充高级特性其实只是相当于完成了优化  
7）我发现我在哪个任务应该在哪个类下面还非常薄弱，因为每次说一个功能应该写在哪个类下面的时候，我经常弄错，怎么刻意练习是个问题，待后续补充  
8）通过一个礼拜类和对象的练习，我终于知道在类 A 中如果要使用类 B 的属性，  
本质是让 A 持有一个 B 的实例对象。这个实例可以在外部创建后作为参数传入 A，而不是必须在 A 内部实例化。之后通过 实例.属性 的方式访问。  
9）有时候一个东西看不懂想不通或者暂时无法完成，不要死磕，先放一会，过几个小时或者第二天再来处理，可能效果会更好
