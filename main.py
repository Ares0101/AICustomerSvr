import asyncio
import json
import uuid
from typing import Optional, Dict, Any
import httpx
from openai import AsyncOpenAI
from agents import (
    Agent,
    Runner,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
    GuardrailFunctionOutput,
    InputGuardrail,
    OutputGuardrail,
    function_tool
)

# ==========================
# 基础配置
# ==========================
set_tracing_disabled(disabled=True)

PROXY = "http://127.0.0.1:7890" #本地代理（使用国内大模型可以不用）

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_API_KEY = ""  # TODO: 替换为你的 DeepSeek key

# ==========================
# OpenAI兼容客户端（DeepSeek）
# ==========================
openai_client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    http_client=httpx.AsyncClient(
        proxy=PROXY,
        timeout=60
    )
)

model = OpenAIChatCompletionsModel(
    model="deepseek-chat",
    openai_client=openai_client
)

# ==========================
# 模拟数据库（真实项目中换成Mongo/Redis/MySQL）
# ==========================
FAKE_USERS = {
    "u001": {
        "name": "张三",
        "phone": "138****1234",
        "orders": [
            {"order_id": "A1001", "status": "已发货", "shipping": "顺丰 SF123456", "amount": 199.0},
            {"order_id": "A1002", "status": "待发货", "shipping": None, "amount": 49.9},
        ]
    }
}

FAKE_REFUNDS = {}     # refund_id -> data
FAKE_COMPLAINTS = {}  # ticket_id -> data


# ==========================
# 工具函数（Tools）
# ==========================
@function_tool
def get_user_profile(user_id: str) -> str:
    """查询用户资料"""
    user = FAKE_USERS.get(user_id)
    if not user:
        return "未找到用户资料"
    return json.dumps(user, ensure_ascii=False)


@function_tool
def list_orders(user_id: str) -> str:
    """列出用户订单"""
    user = FAKE_USERS.get(user_id)
    if not user:
        return "用户不存在"
    return json.dumps(user["orders"], ensure_ascii=False)


@function_tool
def get_order_status(user_id: str, order_id: str) -> str:
    """查询订单状态"""
    user = FAKE_USERS.get(user_id)
    if not user:
        return "用户不存在"

    for o in user["orders"]:
        if o["order_id"] == order_id:
            return json.dumps(o, ensure_ascii=False)

    return "未找到该订单"


@function_tool
def create_refund_request(user_id: str, order_id: str, reason: str) -> str:
    """创建退款申请"""
    refund_id = "R" + str(uuid.uuid4())[:8]

    FAKE_REFUNDS[refund_id] = {
        "refund_id": refund_id,
        "user_id": user_id,
        "order_id": order_id,
        "reason": reason,
        "status": "已提交，等待审核"
    }

    return json.dumps(FAKE_REFUNDS[refund_id], ensure_ascii=False)


@function_tool
def create_complaint_ticket(user_id: str, complaint_text: str) -> str:
    """创建投诉工单"""
    ticket_id = "T" + str(uuid.uuid4())[:8]

    FAKE_COMPLAINTS[ticket_id] = {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "complaint": complaint_text,
        "status": "已受理，等待客服跟进"
    }

    return json.dumps(FAKE_COMPLAINTS[ticket_id], ensure_ascii=False)


@function_tool
def escalate_to_human(user_id: str, reason: str) -> str:
    """升级人工客服"""
    ticket_id = "H" + str(uuid.uuid4())[:8]

    return json.dumps({
        "handoff_ticket": ticket_id,
        "user_id": user_id,
        "reason": reason,
        "status": "已转人工处理"
    }, ensure_ascii=False)


# ==========================
# Guardrail Agent（风险检测）
# ==========================
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

    # 命中高风险就触发 tripwire
    is_blocked = category in ["legal", "medical", "politics", "self_harm"]

    return GuardrailFunctionOutput(
        output_info=data,
        tripwire_triggered=is_blocked
    )


# ==========================
# 输出 Guardrail（防止输出违规）
# ==========================
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


# ==========================
# 业务 Agent：订单客服
# ==========================
order_agent = Agent(
    name="Order Agent",
    model=model,
    handoff_description="订单/物流查询专家",
    tools=[list_orders, get_order_status],
    instructions="""
你是订单客服专家。
你可以调用工具查询用户订单列表、订单状态、物流信息。

要求：
1. 如果用户没有提供订单号，先调用 list_orders(user_id) 给出最近订单并引导用户选择。
2. 如果用户提供了订单号，调用 get_order_status(user_id, order_id) 返回结果。
3. 回复要像真实电商客服，清晰、礼貌。
"""
)


# ==========================
# 业务 Agent：退款客服
# ==========================
refund_agent = Agent(
    name="Refund Agent",
    model=model,
    handoff_description="退款/退货处理专家",
    tools=[list_orders, create_refund_request],
    instructions="""
你是退款客服专家。

要求：
1. 如果用户没给订单号，调用 list_orders(user_id) 并引导用户确认订单号。
2. 如果用户给了订单号，询问退款原因（如果没提供）。
3. 拿到订单号和原因后，调用 create_refund_request(user_id, order_id, reason) 创建退款申请。
4. 回复要包含 refund_id 和处理状态。
"""
)


# ==========================
# 业务 Agent：投诉客服
# ==========================
complaint_agent = Agent(
    name="Complaint Agent",
    model=model,
    handoff_description="投诉与情绪安抚专家",
    tools=[create_complaint_ticket, escalate_to_human],
    instructions="""
你是投诉处理客服。

要求：
1. 先安抚用户情绪，表示理解和歉意。
2. 收集投诉内容（如果用户没说清楚则追问）。
3. 投诉明确后调用 create_complaint_ticket(user_id, complaint_text) 创建工单。
4. 如果用户情绪极端、辱骂威胁、要求报警或媒体曝光，则调用 escalate_to_human(user_id, reason) 转人工。
"""
)


# ==========================
# 人工客服 Agent
# ==========================
human_agent = Agent(
    name="Human Handoff Agent",
    model=model,
    handoff_description="人工客服处理入口",
    tools=[escalate_to_human],
    instructions="""
你负责将用户问题转交人工客服。
直接调用 escalate_to_human(user_id, reason) 并输出工单号。
"""
)


# ==========================
# 分诊 Agent（Triage）
# ==========================
triage_agent = Agent(
    name="Triage Agent",
    model=model,
    instructions="""
你是智能客服分诊系统。
你的任务是判断用户问题属于哪个业务类型，并移交给对应的专家代理。

分类规则：
- 订单、物流、发货、快递、地址修改 -> Order Agent
- 退款、退货、退钱、取消订单 -> Refund Agent
- 投诉、差评、态度差、服务不好、举报 -> Complaint Agent
- 无法分类或用户强烈要求人工 -> Human Handoff Agent

只做分诊，不要回答业务细节。
""",
    handoffs=[order_agent, refund_agent, complaint_agent, human_agent],

    # 输入护栏：拦截法律/医疗/政治/自残等内容
    input_guardrails=[
        InputGuardrail(guardrail_function=input_guardrail)
    ],

    # 输出护栏：防止模型输出违规内容
    output_guardrails=[
        OutputGuardrail(guardrail_function=output_guardrail)
    ]
)


# ==========================
# 主程序
# ==========================
async def main():
    # 模拟上下文（真实场景中来自登录信息）
    context = {"user_id": "u001"}

    tests = [
        "我的订单怎么还没发货？",
        "我要退款，订单A1002",
        "我要投诉你们客服态度太差了！",
        "我想问一下如果我被人诈骗了应该怎么起诉？",
        "我最近心情很差，活着没意思。",
        "上海今天天气怎么样？"
    ]

    for q in tests:
        print("\n" + "=" * 60)
        print("用户问题:", q)

        try:
            result = await Runner.run(triage_agent, q, context=context)
            print("系统回复:", result.final_output)

        except Exception as e:
            print("系统拦截/异常:", str(e))


if __name__ == "__main__":
    asyncio.run(main())
