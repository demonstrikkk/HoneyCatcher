import json
import logging
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from agents.prompts import INTENT_PROMPT, STRATEGY_PROMPT, COACHING_PROMPT, RESPONSE_PROMPT
from config import settings

logger = logging.getLogger(__name__)

_llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name=settings.GROQ_MODEL,
    temperature=0.3,
    max_tokens=256,
)


class AgentState(TypedDict):
    scammer_text: str
    history: List[dict]
    mode: str
    turn_count: int
    intent: Optional[str]
    intent_confidence: Optional[float]
    strategy: Optional[str]
    coaching_text: Optional[str]
    coaching_scripts: Optional[List[str]]
    ai_response: Optional[str]
    error: Optional[str]


def _parse_json(content: str) -> dict:
    try:
        clean = content.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(clean)
    except Exception:
        logger.warning("Failed to parse LLM JSON: %s", content[:200])
        return {}


async def _call_llm(prompt: str) -> dict:
    try:
        response = await _llm.ainvoke([HumanMessage(content=prompt)])
        return _parse_json(response.content)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return {}


async def node_intent(state: AgentState) -> AgentState:
    result = await _call_llm(
        INTENT_PROMPT.format(text=state["scammer_text"])
    )
    return {
        **state,
        "intent": result.get("intent", "unknown"),
        "intent_confidence": result.get("confidence", 0.5),
    }


async def node_strategy(state: AgentState) -> AgentState:
    result = await _call_llm(
        STRATEGY_PROMPT.format(
            intent=state["intent"],
            turn_count=state["turn_count"],
        )
    )
    return {**state, "strategy": result.get("strategy", "empathy")}


async def node_coaching(state: AgentState) -> AgentState:
    history_str = "\n".join(
        f"{m['speaker']}: {m['text']}" for m in state["history"][-3:]
    )
    result = await _call_llm(
        COACHING_PROMPT.format(
            scammer_text=state["scammer_text"],
            intent=state["intent"],
            strategy=state["strategy"],
        )
    )
    return {
        **state,
        "coaching_text": result.get("text", ""),
        "coaching_scripts": result.get("scripts", []),
    }


async def node_response(state: AgentState) -> AgentState:
    history_str = "\n".join(
        f"{m['speaker']}: {m['text']}" for m in state["history"][-3:]
    )
    result = await _call_llm(
        RESPONSE_PROMPT.format(
            scammer_text=state["scammer_text"],
            strategy=state["strategy"],
            history=history_str,
        )
    )
    return {**state, "ai_response": result.get("text", "")}


def _route_mode(state: AgentState) -> str:
    return "coaching" if state["mode"] == "ai_coached" else "response"


def build_agent_graph():
    g = StateGraph(AgentState)

    g.add_node("analyze_intent",    node_intent)
    g.add_node("plan_strategy",     node_strategy)
    g.add_node("generate_coaching", node_coaching)
    g.add_node("generate_response", node_response)

    g.set_entry_point("analyze_intent")
    g.add_edge("analyze_intent", "plan_strategy")
    g.add_conditional_edges("plan_strategy", _route_mode, {
        "coaching": "generate_coaching",
        "response": "generate_response",
    })
    g.add_edge("generate_coaching", END)
    g.add_edge("generate_response", END)

    return g.compile()


agent_graph = build_agent_graph()


async def run_agent(
    scammer_text: str,
    history: list,
    mode: str = "ai_coached",
    turn_count: int = 0,
) -> dict:
    initial: AgentState = {
        "scammer_text": scammer_text,
        "history": history,
        "mode": mode,
        "turn_count": turn_count,
        "intent": None,
        "intent_confidence": None,
        "strategy": None,
        "coaching_text": None,
        "coaching_scripts": None,
        "ai_response": None,
        "error": None,
    }
    result = await agent_graph.ainvoke(initial)
    return result
