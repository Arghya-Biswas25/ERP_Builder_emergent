import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import agents


ANALYSIS = {
    "business_type": "repair services",
    "industry": "electronics",
    "scale": "small",
    "suggested_modules": ["CRM", "Inventory Management", "Finance & Accounting"],
    "key_requirements": ["customer intake", "job tracking", "inventory", "billing"],
    "summary": "ERP for a small repair business.",
}


def test_requirement_gatherer_forces_completion_after_enough_user_answers(monkeypatch):
    conversation_history = [
        {"role": "user", "content": "Initial ERP prompt"},
        {"role": "assistant", "content": "First question"},
        {"role": "user", "content": "First answer"},
        {"role": "assistant", "content": "Second question"},
        {"role": "user", "content": "Second answer"},
    ]

    async def fake_call_llm(messages, temperature=0.7, max_tokens=4000, timeout=None, model_group="default"):
        return json.dumps(
            {
                "complete": False,
                "question": "A third question that should not be asked",
                "current_module": "Finance & Accounting",
                "progress_summary": "Collected enough detail already.",
            }
        )

    monkeypatch.setattr(agents, "call_llm", fake_call_llm)

    result = asyncio.run(agents.requirement_gatherer(ANALYSIS, conversation_history))

    assert result["complete"] is True
    assert isinstance(result["requirements"], dict)
    assert result["requirements"]["business_type"] == "repair services"


def test_requirement_gatherer_allows_follow_up_before_threshold(monkeypatch):
    conversation_history = [
        {"role": "user", "content": "Initial ERP prompt"},
        {"role": "assistant", "content": "First question"},
        {"role": "user", "content": "First answer"},
    ]

    async def fake_call_llm(messages, temperature=0.7, max_tokens=4000, timeout=None, model_group="default"):
        return json.dumps(
            {
                "complete": False,
                "question": "One more follow-up",
                "current_module": "Inventory Management",
                "progress_summary": {"captured": ["repair tickets", "notifications"]},
            }
        )

    monkeypatch.setattr(agents, "call_llm", fake_call_llm)

    result = asyncio.run(agents.requirement_gatherer(ANALYSIS, conversation_history))

    assert result["complete"] is False
    assert result["question"] == "One more follow-up"
    assert result["progress_summary"] == "captured: repair tickets, notifications"
