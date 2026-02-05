"""
Speech Naturalization Service
Converts written AI text into natural sounding spoken language
"""

import logging
from typing import Optional
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from agents.prompts import SPEECH_NATURALIZATION_PROMPT
from config import settings

logger = logging.getLogger("speech_naturalizer")

class SpeechNaturalizer:
    """
    Converts written responses into natural spoken language
    """
    
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
    
    def _get_llm(self):
        return self.llm if self.llm else self.fallback_llm
    
    async def naturalize(
        self,
        written_text: str,
        language: str = "en"
    ) -> str:
        """
        Convert written text to natural spoken language
        
        Args:
            written_text: The AI-generated written response
            language: Language code for language-specific naturalizations
            
        Returns:
            Naturalized spoken text
        """
        llm = self._get_llm()
        
        # Fallback if no LLM available
        if not llm:
            logger.warning("No LLM available for speech naturalization, using rule-based fallback")
            return self._rule_based_naturalization(written_text)
        
        try:
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", SPEECH_NATURALIZATION_PROMPT),
                ("user", "Language: {language}\n\nText to naturalize:\n{text}")
            ])
            
            # Chain
            chain = prompt | llm | StrOutputParser()
            
            # Invoke
            result = await chain.ainvoke({
                "language": language,
                "text": written_text
            })
            
            logger.info(f"Speech naturalization complete: {language}")
            return result.strip()
            
        except Exception as e:
            logger.error(f"Speech naturalization failed: {e}", exc_info=True)
            return self._rule_based_naturalization(written_text)
    
    def _rule_based_naturalization(self, text: str) -> str:
        """
        Fallback rule-based naturalization when LLM unavailable
        Simple contractions and basic fillers for a more human feel.
        """
        # Basic contractions
        replacements = {
            " I am ": " I'm ",
            " you are ": " you're ",
            " do not ": " don't ",
            " cannot ": " can't ",
            " will not ": " won't ",
            " should not ": " shouldn't ",
            " would not ": " wouldn't ",
            " is not ": " isn't ",
            " are not ": " aren't ",
            " it is ": " it's ",
            " that is ": " that's ",
            " fine ": " okay... ",
            " please ": " like, ",
            " hello ": " hello? ",
            " goodbye ": " yeah, bye ",
        }
        
        naturalized = text
        for formal, casual in replacements.items():
            naturalized = naturalized.replace(formal, casual)
        
        # Add human noise (fillers & breathers)
        import random
        # 40% chance to add a filler at start
        if random.random() < 0.4:
            fillers = ["um, ", "uh, ", "actually... ", "so, ", "wait... ", "I mean, "]
            naturalized = random.choice(fillers) + naturalized
            
        # Add a pause/stammer in the middle for longer sentences
        if len(naturalized) > 50 and " " in naturalized:
            words = naturalized.split(" ")
            mid = len(words) // 2
            if random.random() < 0.3:
                words[mid] = words[mid] + "... uh..."
                naturalized = " ".join(words)
        
        return naturalized.strip()


# Singleton instance
speech_naturalizer = SpeechNaturalizer()
