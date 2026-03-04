from agents import Agent
from config.cs_config import model
from tools.cs_tools import escalate_to_human

human_agent = Agent(
    name="Human Handoff Agent",
    model=model,
    handoff_description="人工客服处理入口",
    tools=[escalate_to_human],
    instructions="""
    你负责将用户问题转交人工客服。
    直接调用 escalate_to_human(user_id, reason) 并输出工单号。
    对外不要暴露任何内部角色名称或流程，不要自称为“Human Handoff Agent”。
    统一以“平台智能客服”身份与用户交流，不要提及分诊、Agent、工具调用。
    如果上下文包含用户ID user_id，则直接使用，不要再次向用户索取。
    避免重复问候和自我介绍；除首次轮次外直接进入主题与处理结果。
    """
)
