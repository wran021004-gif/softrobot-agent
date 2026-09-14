"""Executable allowlist. Descriptive legacy manifests never grant execution."""
from schemas.workbench import Decision, WorkbenchResult, NoArguments, EvaluationArguments, EvidenceArguments
from schemas.workbench import CandidateArguments, CreateCandidateArguments, CompareCandidatesArguments

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
    'read_evidence': dict(label='按需读取证据', schema=EvidenceArguments, requires=[], permission='read_evidence',
                          cost={}, purpose='按 evidence_id 和 JSON Pointer 读取字段或有限片段；catalog:cNNN 的 /entries 为候选文件目录；返回 cite_as 可直接引用'),
}
DESIGN_TOOLS = {
    'create_candidate': dict(label='根据评价修改候选', schema=CreateCandidateArguments, requires=[], permission='candidate_design',
                            cost={'candidates': 1}, purpose='只修改权威 envelope 允许的参数；必须引用 parent_id 的本轮评价证据，不能提前生成序列'),
    'check_candidate': dict(label='独立检查候选', schema=CandidateArguments, requires=[], permission='analysis',
                           cost={}, purpose='检查指定候选的语法、范围与关系约束，生成独立 IR 和 PCC 局部分析'),
    'evaluate_candidate': dict(label='真实评价候选', schema=CandidateArguments, requires=['check_candidate'], permission='simulate',
                              cost={'simulations': 1, 'matlab_calls': 3}, purpose='指定候选经原 Harness 的 MATLAB M0/M1/形状、C1、编译、MuJoCo 和冻结评价；成功与失败均返回真实数据'),
    'compare_candidates': dict(label='比较候选真实成绩', schema=CompareCandidatesArguments, requires=[], permission='read_evidence',
                              cost={}, purpose='仅比较指定候选已有的本轮评价；任务状态与误差来自既有评价程序'),
    'observe_candidate': dict(label='观察候选轨迹', schema=CandidateArguments, requires=['evaluate_candidate'], permission='derived_artifacts',
                             cost={}, purpose='用原观察器从指定候选保存数据生成动画和曲线，不重新仿真'),
}
LEGACY_TOOLS = set(TOOLS)
TOOLS.update(DESIGN_TOOLS)
PERMISSIONS = sorted({v['permission'] for v in TOOLS.values()})
LIMITS = dict(tool_calls=10, decisions=14, simulations=1, matlab_calls=2)


def executable_catalog():
    return {name: {**{k: v for k, v in info.items() if k != 'schema'},
                   'input_schema': info['schema'].model_json_schema(), 'output_schema': 'WorkbenchResult',
                   'implementation_status': 'IMPLEMENTED', 'executable': True,
                   'cost_note': 'evaluate_design 在 request.replay 模式为零后端；模型不能修改 request 或切换模式',
                   'failure_codes': ['INVALID_INPUT', 'TOOL_ERROR', 'TIMEOUT', 'CAPABILITY_MISSING',
                                     'PERMISSION_DENIED', 'BUDGET_EXHAUSTED', 'EVIDENCE_CHANGED', 'INTERRUPTED'],
                   'tool_id': 'workbench.'+name, 'tool_version': '1.1.0',
                   'limitations': '冻结 reach_free、C1；设计范围和候选数由保存 session 的 envelope 与预算决定；无标定、编程或硬件权限'}
            for name, info in TOOLS.items()}


def catalog():
    from capabilities.registry import query_tools
    from tools.public_catalog import catalog as public_catalog
    from schemas.dynamic_workbench import native_tools as dynamic_tools
    return dict(public=public_catalog(), executable=executable_catalog(), limits=LIMITS,
                dynamics_v2=dict(entrypoint='python examples/workbench.py dynamics',
                    executable=dynamic_tools(),grant='configs/experiments/round9_grant.json',
                    implementation='tools/dynamic_campaign.py',scope='New reach_free campaign; original V1 continuation remains strict'),
                decision_schema=Decision.model_json_schema(), result_schema=WorkbenchResult.model_json_schema(),
                library=[{**v, 'executable_via_workbench': False,
                          'execution_note': '库工具或历史实验入口；不在执行白名单，不能由决策直接调用'}
                         for v in query_tools()],
                missing=['hardware execution', 'calibrated physics', 'C3/RL',
                         'design/control proposals beyond frozen C1 route'])
