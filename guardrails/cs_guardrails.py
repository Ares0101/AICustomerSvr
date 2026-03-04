import json
from agents import Agent, Runner, GuardrailFunctionOutput
from config.cs_config import model

risk_guard_agent = Agent(
    name="Risk Guard Agent",
    model=model,
    instructions="""
    你是一个严格的风险分类器，用于客服系统的输入安全检测。
    你必须只输出JSON，不允许输出任何其他内容。
    你需要判断用户输入是否属于以下风险类别：
    - legal: 法律咨询/违法行为
    - medical: 医疗诊断/用药建议
    - politics: 政治敏感内容
    - self_harm: 自残/暴力威胁/极端情绪
    - normal: 正常客服业务（订单/退款/投诉/物流等）
    输出格式：
    {"category": "normal/legal/medical/politics/self_harm", "reasoning": "原因"}
    """
)


async def input_guardrail(ctx, agent, input_data):
    result = await Runner.run(risk_guard_agent, input_data, context=ctx.context)
    raw = result.final_output
    try:
        data = json.loads(raw)
    except Exception:
        data = {"category": "self_harm", "reasoning": "模型输出无法解析，默认高风险"}
    category = data.get("category", "self_harm")
    is_blocked = category in ["legal", "medical", "politics", "self_harm"]
    return GuardrailFunctionOutput(
        output_info=data,
        tripwire_triggered=is_blocked
    )


output_guard_agent = Agent(
    name="Output Guard Agent",
    model=model,
    instructions="""
    你是一个输出安全审查器。
    你必须判断助手输出是否包含以下风险内容：
    - 医疗建议（用药、诊断）
    - 法律建议（诉讼、规避法律）
    - 政治敏感煽动
    - 暴力/自残引导
    - 诈骗、黑产指导
    你必须只输出JSON：
    {"safe": true/false, "reasoning": "..."}
    """
)


async def output_guardrail(ctx, agent, output_text: str):
    result = await Runner.run(output_guard_agent, output_text, context=ctx.context)
    raw = result.final_output
    try:
        data = json.loads(raw)
    except Exception:
        data = {"safe": False, "reasoning": "无法解析审查输出，默认不安全"}
    safe = bool(data.get("safe", False))
    return GuardrailFunctionOutput(
        output_info=data,
        tripwire_triggered=not safe
    )
