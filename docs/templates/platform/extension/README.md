# 最小扩展包模板

`contracts.py / implementation.py / manifest.py / __init__.py` 是可复制运行的数学扩展包；复制到 `extensions/example_math/` 后，发现程序会登记 `analysis.example_square`。不编辑公共循环；在新会话策略允许该工具后调用。目录内其他 `*_skeleton.py` 是明确待实现的接口骨架，不能将其未实现方法登记为可执行能力。

```powershell
python examples/workbench.py platform catalog
# 给新会话 policy.tool_bindings 加 analysis.example_square: '1.0.0'；不要修改已冻结会话。
# ToolRequest.arguments = {length_m: 2.0, frame: world}
```

输出应是 `area_m2=4.0`，scope 为 mathematical_only；这不是机器人物理模型。开发者还需给实际扩展添加适用范围及自己的最小测试。

后端／控制／搜索／诊断／工作者的完整可执行参考见 `extensions/reference`、`tools/platform_tools.py` 和 `tools/platform_worker.py`。骨架只展示接口责任，不补造未来物理或科研阈值。
