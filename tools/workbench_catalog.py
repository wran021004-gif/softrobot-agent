"""Executable allowlist. Descriptive legacy manifests never grant execution."""
from schemas.workbench import Decision, WorkbenchResult, NoArguments, EvaluationArguments, EvidenceArguments

TOOLS = {
    'inspect_task': dict(label='读取任务与检查设计', schema=NoArguments, requires=[], permission='read_inputs',
                         cost={}, purpose='解析冻结合同、设计语法及工具适用性'),
    'analyze_design': dict(label='数学分析', schema=NoArguments, requires=['inspect_task'], permission='analysis',
                           cost={}, purpose='现有 PCC 直态局部雅可比；不判断任务成绩'),
    'evaluate_design': dict(label='控制生成、编译、仿真与评价', schema=EvaluationArguments,
                            requires=['inspect_task', 'analyze_design'], permission='simulate',
                            cost={'simulations': 1, 'matlab_calls': 2},
                            purpose='原 Harness 完整评价；或请求创建时登记的封存历史运行回放（零后端，单独标明历史成绩）；整次候选为恢复边界'),
    'diagnose': dict(label='分析反馈', schema=NoArguments, requires=['evaluate_design'], permission='read_evidence',
                     cost={}, purpose='读取原评价和诊断证据；因果归因保持 UNKNOWN'),
    'observe': dict(label='生成动画与曲线', schema=NoArguments, requires=['evaluate_design'], permission='derived_artifacts',
                    cost={}, purpose='复用 ObservationViewer；保存数据回放，零动力学调用'),
    'read_evidence': dict(label='读取历史证据', schema=EvidenceArguments, requires=[], permission='read_evidence',
                          cost={}, purpose='只能按已登记证据 ID 读取 JSON；禁止任意文件路径'),
}
PERMISSIONS = sorted({v['permission'] for v in TOOLS.values()})
LIMITS = dict(tool_calls=10, decisions=14, simulations=1, matlab_calls=2)


def executable_catalog():
    return {name: {**{k: v for k, v in info.items() if k != 'schema'},
                   'input_schema': info['schema'].model_json_schema(), 'output_schema': 'WorkbenchResult',
                   'implementation_status': 'IMPLEMENTED', 'executable': True,
                   'cost_note': 'evaluate_design 在 request.replay 模式为零后端；模型不能修改 request 或切换模式',
                   'failure_codes': ['INVALID_INPUT', 'TOOL_ERROR', 'TIMEOUT', 'CAPABILITY_MISSING',
                                     'PERMISSION_DENIED', 'BUDGET_EXHAUSTED', 'EVIDENCE_CHANGED', 'INTERRUPTED'],
                   'limitations': '冻结 reach_free、语法内设计、C1；无搜索、标定、写代码、硬件或网络权限'}
            for name, info in TOOLS.items()}


def catalog():
    from capabilities.registry import query_tools
    return dict(executable=executable_catalog(), limits=LIMITS,
                decision_schema=Decision.model_json_schema(), result_schema=WorkbenchResult.model_json_schema(),
                library=[{**v, 'executable_via_workbench': False,
                          'execution_note': '库工具或历史实验入口；不在执行白名单，不能由决策直接调用'}
                         for v in query_tools()],
                missing=['LLM adapter', 'hardware execution', 'calibrated physics', 'C3/RL',
                         'design/control proposals beyond frozen C1 route'])
