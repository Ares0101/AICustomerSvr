import json
import re
import uuid
from collections import deque
import os
import tornado.ioloop
import tornado.web
from agents import Runner
from cs_agents.cs_triage_agent import triage_agent

SESSIONS = {}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "web"))


class IndexHandler(tornado.web.RequestHandler):
    async def get(self):
        self.render("index.html")


class ChatHandler(tornado.web.RequestHandler):
    async def post(self):
        try:
            data = json.loads(self.request.body.decode("utf-8"))
        except Exception:
            self.set_status(400)
            self.finish({"error": "invalid json"})
            return
        msg = (data.get("message") or "").strip()
        session_id = data.get("session_id")
        user_id = data.get("user_id") or "u001"
        if not session_id or session_id not in SESSIONS:
            session_id = uuid.uuid4().hex
            SESSIONS[session_id] = {"history": deque(maxlen=12), "greeted": False, "user_id": user_id}
        state = SESSIONS[session_id]
        if user_id:
            state["user_id"] = user_id
        memory_lines = []
        if state.get("user_id"):
            memory_lines.append(f"用户ID: {state['user_id']}")
        if state["history"]:
            memory_lines.append("最近对话:")
            for role, content in list(state["history"])[-6:]:
                memory_lines.append(f"{role}: {content}")
        memory_text = "\n".join(memory_lines)
        composed = (
            f"【会话上下文】\n{memory_text}\n\n"
            f"【当前用户输入】\n{msg}\n\n"
            "【指令】\n"
            "- 基于上下文连续对话，除首次外不要重复问候或自我介绍。\n"
            "- 如上下文包含用户ID则直接使用，不要再次索取。\n"
            "- 统一以平台智能客服身份应答，不要透露内部角色或流程。\n"
        )
        context = {"user_id": state.get("user_id")}
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
        if state["greeted"]:
            text_lines = [ln for ln in text.splitlines() if not re.search(greet_pattern, ln)]
            text = "\n".join(text_lines).strip()
        else:
            if re.search(greet_pattern, text):
                state["greeted"] = True
        state["history"].append(("用户", msg))
        state["history"].append(("系统", text))
        self.finish({"session_id": session_id, "reply": text})


def make_app():
    settings = {
        "template_path": WEB_DIR,
        "static_path": WEB_DIR,
        "autoreload": False,
        "debug": False,
    }
    return tornado.web.Application([
        (r"/", IndexHandler),
        (r"/api/chat", ChatHandler),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": settings["static_path"]}),
    ], **settings)


if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    print("http://localhost:8888/")
    tornado.ioloop.IOLoop.current().start()
