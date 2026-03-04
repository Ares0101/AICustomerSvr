import asyncio
import re
from collections import deque
from agents import Runner
from cs_agents.cs_triage_agent import triage_agent


async def main():
    context = {"user_id": "u001"}
    history = deque(maxlen=6)
    greeted = False
    print("智能客服系统已启动（输入 exit 退出）")
    print("=" * 60)
    while True:
        try:
            q = input("\n用户: ").strip()
            if q.lower() in ["exit", "quit", "q"]:
                print("系统已退出。")
                break
            if not q:
                continue
            print("-" * 60)
            memory_lines = []
            if context.get("user_id"):
                memory_lines.append(f"用户ID: {context['user_id']}")
            if history:
                memory_lines.append("最近对话:")
                for role, content in list(history)[-4:]:
                    memory_lines.append(f"{role}: {content}")
            memory_text = "\n".join(memory_lines)
            composed = (
                f"【会话上下文】\n{memory_text}\n\n"
                f"【当前用户输入】\n{q}\n\n"
                "【指令】\n"
                "- 基于上下文连续对话，除首次外不要重复问候或自我介绍。\n"
                "- 如上下文包含用户ID则直接使用，不要再次索取。\n"
            )
            result = await Runner.run(triage_agent, composed, context=context)
            text = result.final_output or ""
            prefixes = [
                "Order Agent", "Refund Agent", "Complaint Agent", "Human Handoff Agent",
                "Triage Agent", "Risk Guard Agent", "Output Guard Agent"
            ]
            pattern = r"^(?:\s*(?:" + "|".join(re.escape(p) for p in prefixes) + r")\s*[:：\-]\s*)+"
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            lines = text.splitlines()
            cleaned_lines = []
            for line in lines:
                line2 = re.sub(pattern, "", line, flags=re.IGNORECASE)
                cleaned_lines.append(line2)
            text = "\n".join(cleaned_lines).strip()
            greet_pattern = r"^(?:您?好|你好)[！!，,。]*\s*我是.*平台智能客服.*"
            text_lines = text.splitlines()
            if greeted:
                text_lines = [ln for ln in text_lines if not re.search(greet_pattern, ln)]
            text = "\n".join(text_lines).strip()
            if not greeted and any(re.search(greet_pattern, ln) for ln in text_lines):
                greeted = True
            print("系统:", text)
            history.append(("用户", q))
            history.append(("系统", text))
        except KeyboardInterrupt:
            print("\n检测到 Ctrl+C，系统退出。")
            break
        except Exception as e:
            print("系统拦截/异常:", str(e))


if __name__ == "__main__":
    asyncio.run(main())
