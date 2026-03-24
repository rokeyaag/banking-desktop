import json
from uuid import UUID
from sqlalchemy.orm import Session
from app.db.models import AIFlow, FlowStatus, AccountType
import logging
_log = logging.getLogger(__name__)

FLOWS = {
    "open_account": [
        {"step": "account_type", "prompt": "🏦 Welcome! Let's open a new account.\n\nSelect account type:\n1. Checking\n2. Savings\n3. Business", "key": "account_type"},
        {"step": "holder_name",  "prompt": "👤 Enter the full name of the account holder:", "key": "holder_name"},
        {"step": "dob",          "prompt": "🎂 Enter date of birth (DD/MM/YYYY):", "key": "dob"},
        {"step": "nid",          "prompt": "🪪 Enter NID / Passport number:", "key": "nid"},
        {"step": "phone",        "prompt": "📞 Enter phone number:", "key": "phone"},
        {"step": "address",      "prompt": "🏠 Enter full address:", "key": "address"},
        {"step": "occupation",   "prompt": "💼 Enter occupation (e.g. Engineer, Student, Business):", "key": "occupation"},
        {"step": "currency",     "prompt": "💱 Select currency:\n1. BDT\n2. USD\n3. EUR\n4. GBP", "key": "currency"},
        {"step": "initial",      "prompt": "💰 Enter initial deposit amount (enter 0 to skip):", "key": "initial_deposit"},
        {"step": "confirm",      "prompt": "✅ Please confirm the following details:\n\n👤 Holder: {holder_name}\n🏦 Type: {account_type}\n🎂 DOB: {dob}\n🪪 NID: {nid}\n📞 Phone: {phone}\n🏠 Address: {address}\n💼 Occupation: {occupation}\n💱 Currency: {currency}\n💰 Deposit: {initial_deposit}\n\nType YES to confirm or NO to cancel:", "key": "confirm"},
    ],
    "deposit": [
        {"step": "select_account", "prompt": "💳 Enter account number:", "key": "account_number"},
        {"step": "amount",         "prompt": "💰 Enter deposit amount:", "key": "amount"},
        {"step": "pin",            "prompt": "🔐 Enter your PIN:", "key": "pin"},
        {"step": "confirm",        "prompt": "✅ Deposit ${amount} into account {account_number}?\nType YES / NO:", "key": "confirm"},
    ],
    "check_balance": [
        {"step": "select_account", "prompt": "💳 Enter account number (type 'all' to see all accounts):", "key": "account_identifier"},
    ],
}


def start_flow(db: Session, user_id: UUID, flow_type: str) -> tuple[bool, str, UUID | None]:
    if flow_type not in FLOWS:
        return False, f"Unknown flow: {flow_type}", None
    flow = AIFlow(
        user_id=user_id, flow_type=flow_type,
        current_step=FLOWS[flow_type][0]["step"],
        status=FlowStatus.ACTIVE, state_json=json.dumps({})
    )
    db.add(flow)
    db.flush()
    db.refresh(flow)
    flow_id = flow.id
    return True, FLOWS[flow_type][0]["prompt"], flow_id


def process_flow_input(db: Session, flow_id: UUID, user_id: UUID, user_input: str) -> tuple[bool, str, bool]:
    flow = db.query(AIFlow).filter(AIFlow.id == flow_id, AIFlow.user_id == user_id).first()
    if not flow or flow.status != FlowStatus.ACTIVE:
        return False, "Flow not found or inactive.", False

    steps = FLOWS[flow.flow_type]
    state = json.loads(flow.state_json or "{}")
    idx = next((i for i, s in enumerate(steps) if s["step"] == flow.current_step), None)
    if idx is None:
        return False, "Invalid state.", False

    key = steps[idx]["key"]
    inp = user_input.strip()

    if key == "account_type":
        m = {"1": "CHECKING", "2": "SAVINGS", "3": "BUSINESS",
             "checking": "CHECKING", "savings": "SAVINGS", "business": "BUSINESS"}
        val = m.get(inp.lower())
        if not val:
            return True, "⚠ Please enter 1, 2, or 3.", False
        state["account_type"] = val

    elif key == "holder_name":
        if len(inp) < 2:
            return True, "⚠ Please enter a valid name.", False
        state["holder_name"] = inp

    elif key == "dob":
        state["dob"] = inp if inp else "N/A"

    elif key == "nid":
        state["nid"] = inp if inp else "N/A"

    elif key == "phone":
        state["phone"] = inp if inp else "N/A"

    elif key == "address":
        if len(inp) < 3:
            return True, "⚠ Please enter a complete address.", False
        state["address"] = inp

    elif key == "occupation":
        state["occupation"] = inp if inp else "N/A"

    elif key == "currency":
        m = {"1": "BDT", "2": "USD", "3": "EUR", "4": "GBP",
             "bdt": "BDT", "usd": "USD", "eur": "EUR", "gbp": "GBP"}
        val = m.get(inp.lower())
        if not val:
            return True, "⚠ Please enter 1, 2, 3, or 4.", False
        state["currency"] = val

    elif key == "initial_deposit":
        try:
            v = float(inp) if inp else 0.0
            if v < 0: raise ValueError
            state["initial_deposit"] = str(v)
        except ValueError:
            return True, "⚠ Please enter a valid amount (e.g. 500).", False

    elif key == "amount":
        try:
            v = float(inp)
            if v <= 0: raise ValueError
            state["amount"] = str(v)
        except ValueError:
            return True, "⚠ Please enter a valid amount.", False

    elif key == "account_number":
        state["account_number"] = inp

    elif key == "account_identifier":
        state["account_identifier"] = inp

    elif key == "pin":
        state["pin"] = inp

    elif key == "confirm":
        if inp.upper() == "NO":
            flow.status = FlowStatus.CANCELLED
            return True, "❌ Operation cancelled.", True
        if inp.upper() != "YES":
            return True, "Please type YES or NO.", False

    flow.state_json = json.dumps(state)

    next_idx = idx + 1
    if next_idx >= len(steps):
        result = _execute_flow(db, flow, state, user_id)
        flow.status = FlowStatus.COMPLETED
        flow.state_json = json.dumps({k: v for k, v in state.items() if k != "pin"})
        return True, result, True

    next_step = steps[next_idx]
    flow.current_step = next_step["step"]
    try:
        prompt = next_step["prompt"].format(**state)
    except KeyError:
        prompt = next_step["prompt"]
    return True, prompt, False


def _execute_flow(db: Session, flow: AIFlow, state: dict, user_id: UUID) -> str:
    if flow.flow_type == "open_account":
        from app.services.account_service import open_account
        acc_type = AccountType(state.get("account_type", "CHECKING"))
        ok, msg, account = open_account(
            db, user_id, acc_type,
            initial_deposit=float(state.get("initial_deposit", 0) or 0),
            holder_name=state.get("holder_name", ""),
            dob=state.get("dob", ""),
            nid=state.get("nid", ""),
            phone=state.get("phone", ""),
            address=state.get("address", ""),
            occupation=state.get("occupation", ""),
            currency=state.get("currency", "USD"),
        )
        if ok and account:
            return (
                f"✅ Account opened successfully!\n\n"
                f"Account Number: {account['account_number']}\n"
                f"Holder: {state.get('holder_name')}\n"
                f"Type: {acc_type.value.title()}\n"
                f"Currency: {state.get('currency')}\n"
                f"Balance: ${account['balance']:,.2f}"
            )
        return f"❌ {msg}"

    elif flow.flow_type == "deposit":
        from app.services.account_service import get_account_by_number
        from app.services.deposit_service import deposit
        acct = get_account_by_number(db, state.get("account_number", ""), user_id)
        if not acct: return "❌ Account not found."
        ok, msg, _ = deposit(db, user_id, acct.id, state.get("amount", "0"), state.get("pin", ""))
        return f"✅ {msg}" if ok else f"❌ {msg}"

    elif flow.flow_type == "check_balance":
        from app.services.account_service import list_accounts, get_account_by_number
        ident = state.get("account_identifier", "").strip().lower()
        if ident == "all":
            accts = list_accounts(db, user_id)
            if not accts: return "No accounts found."
            lines = "\n".join(
                f"• {a['account_number']}: ${a['balance']:,.2f} ({a['account_type'].value.title()})"
                for a in accts
            )
            return f"Your accounts:\n{lines}"
        acct = get_account_by_number(db, ident, user_id)
        if not acct: return "❌ Account not found."
        return f"💰 Balance: ${acct.balance:,.2f}"

    return "✅ Done."