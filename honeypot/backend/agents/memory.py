# memory.py
# Currently LangGraph manages state ephemeral per run, 
# and we persist history in MongoDB in the main loop.
# This file is a placeholder for more advanced memory operations if needed.

class AgentMemory:
    def get_context(self, session_id: str):
        pass

    def save_context(self, session_id: str, data: dict):
        pass
