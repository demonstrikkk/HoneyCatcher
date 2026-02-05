import os
import operator
from typing import Annotated, Sequence, TypedDict, Union, List, Dict
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from agents.prompts import (
    SYSTEM_PROMPT, 
    PERSONA_PROMPT, 
    INTENT_ANALYSIS_PROMPT, 
    RESPONSE_PLANNER_PROMPT, 
    HUMANIZER_PROMPT
)
from config import settings

# State Definition
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    intent: str
    emotion: str
    strategy: str
    draft_response: str
    final_response: str
    turn_count: int

class HoneyPotAgent:
    def __init__(self):
        self.groq_key = settings.GROQ_API_KEY
        self.gemini_key = settings.GEMINI_API_KEY
        
        # Primary LLM (Groq)
        if self.groq_key:
            self.llm = ChatGroq(temperature=0.7, model_name="llama-3.3-70b-versatile", api_key=self.groq_key)
        else:
            self.llm = None
            
        # Fallback (Gemini)
        if self.gemini_key:
            self.fallback_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=self.gemini_key)
        else:
            self.fallback_llm = None

        self.workflow = self._build_graph()

    def _get_llm(self):
        return self.llm if self.llm else self.fallback_llm

    def _analyze_intent(self, state: AgentState):
        """Node 1: Analyze scamer intent"""
        messages = state["messages"]
        last_msg = messages[-1].content
        
        llm = self._get_llm()
        if not llm:
             return {"intent": "scam", "emotion": "aggressive", "strategy": "stall"}

        # New pattern: System prompt + User input
        prompt = ChatPromptTemplate.from_messages([
            ("system", INTENT_ANALYSIS_PROMPT),
            ("user", "{input}")
        ])
        
        chain = prompt | llm | JsonOutputParser()
        
        try:
            result = chain.invoke({"input": last_msg})
            return {
                "intent": result.get("intent", "unknown"),
                "emotion": result.get("emotion", "neutral"),
                "strategy": result.get("strategy", "stall")
            }
        except Exception as e:
             # logger.warning(f"Intent analysis failed: {e}")
             return {"intent": "unknown", "emotion": "neutral", "strategy": "stall"}

    def _generate_response(self, state: AgentState):
        """Node 2: Generate draft response"""
        # Format history simply
        history_text = "\n".join([f"{m.type}: {m.content}" for m in state["messages"][-5:]])
        
        # Combine System + Persona + Strategy + History
        full_system_prompt = f"{SYSTEM_PROMPT}\n\n{PERSONA_PROMPT}\n\n{RESPONSE_PLANNER_PROMPT}"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", full_system_prompt),
            ("user", "Context: {history}\nStrategy: {strategy}")
        ])
        
        llm = self._get_llm()
        if not llm:
            return {"draft_response": "I am not sure what do you mean. Can you explain?"}

        chain = prompt | llm | StrOutputParser()
        
        try:
            result = chain.invoke({
                "history": history_text,
                "strategy": state["strategy"]
            })
            return {"draft_response": result}
        except Exception:
            return {"draft_response": "I am confused."}

    def _humanize(self, state: AgentState):
        """Node 3: Humanize the output"""
        draft = state["draft_response"]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", HUMANIZER_PROMPT),
            ("user", "Input: {text}")
        ])
        
        llm = self._get_llm()
        if not llm:
             return {"final_response": draft, "turn_count": state["turn_count"] + 1}

        chain = prompt | llm | StrOutputParser()
        
        try:
            result = chain.invoke({"text": draft})
        except:
            result = draft
            
        return {"final_response": result, "turn_count": state["turn_count"] + 1}

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        workflow.add_node("analyze", self._analyze_intent)
        workflow.add_node("generate", self._generate_response)
        workflow.add_node("humanize", self._humanize)
        
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "generate")
        workflow.add_edge("generate", "humanize")
        workflow.add_edge("humanize", END)
        
        return workflow.compile()

    async def run(self, history: List[Dict[str, str]]):
        """
        Run the agent graph.
        History format: [{"role": "scammer", "content": "..."}, ...]
        """
        lc_messages = []
        for h in history:
            if h["role"] == "scammer":
                lc_messages.append(HumanMessage(content=h["content"]))
            elif h["role"] == "agent":
                lc_messages.append(AIMessage(content=h["content"]))
        
        initial_state = {
            "messages": lc_messages,
            "turn_count": 0,
            "intent": "",
            "emotion": "",
            "strategy": "",
            "draft_response": "",
            "final_response": ""
        }
        
        try:
            result = await self.workflow.ainvoke(initial_state)
            return result.get("final_response", "I am sorry, I didn't understand that.")
        except Exception as e:
            import logging
            logging.error(f"Agent graph error: {e}", exc_info=True)
            return f"I... am having trouble with my computer."

agent_system = HoneyPotAgent()
