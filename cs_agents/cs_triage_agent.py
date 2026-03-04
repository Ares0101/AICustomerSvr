from agents import Agent, InputGuardrail, OutputGuardrail
from config.cs_config import model
from guardrails.cs_guardrails import input_guardrail, output_guardrail
from cs_agents.cs_order_agent import order_agent
from cs_agents.cs_refund_agent import refund_agent
from cs_agents.cs_complaint_agent import complaint_agent
from cs_agents.cs_human_agent import human_agent

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
    不要向用户透露任何内部角色名称或流程，统一以“平台智能客服”对外呈现。
    如果上下文包含用户ID user_id，则直接使用，不要再次向用户索取。
    避免重复问候和自我介绍；除首次轮次外直接进入主题与处理结果。
    """,
    handoffs=[order_agent, refund_agent, complaint_agent, human_agent],
    input_guardrails=[InputGuardrail(guardrail_function=input_guardrail)],
    output_guardrails=[OutputGuardrail(guardrail_function=output_guardrail)]
)
