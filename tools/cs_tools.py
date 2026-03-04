import json
import uuid
from agents import function_tool

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

FAKE_REFUNDS = {}
FAKE_COMPLAINTS = {}


@function_tool
def get_user_profile(user_id: str) -> str:
    user = FAKE_USERS.get(user_id)
    if not user:
        return "未找到用户资料"
    return json.dumps(user, ensure_ascii=False)


@function_tool
def list_orders(user_id: str) -> str:
    user = FAKE_USERS.get(user_id)
    if not user:
        return "用户不存在"
    return json.dumps(user["orders"], ensure_ascii=False)


@function_tool
def get_order_status(user_id: str, order_id: str) -> str:
    user = FAKE_USERS.get(user_id)
    if not user:
        return "用户不存在"
    for o in user["orders"]:
        if o["order_id"] == order_id:
            return json.dumps(o, ensure_ascii=False)
    return "未找到该订单"


@function_tool
def create_refund_request(user_id: str, order_id: str, reason: str) -> str:
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
    ticket_id = "H" + str(uuid.uuid4())[:8]
    return json.dumps({
        "handoff_ticket": ticket_id,
        "user_id": user_id,
        "reason": reason,
        "status": "已转人工处理"
    }, ensure_ascii=False)
