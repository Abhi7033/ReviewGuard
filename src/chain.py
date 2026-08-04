from .models import ReviewAnalysis
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

load_dotenv()


def build_analysis_chain(provider: str = "google_genai:gemini-3.5-flash"):
    """
    TODO:
      1. Create a ChatPromptTemplate (system + human) for the analysis task.
      2. init_chat_model(provider) - this is the one-line-swap magic.
      3. Bind structured output to ReviewAnalysis (with_structured_output).
      4. Return the composed chain:  prompt | model_with_structure
    Concept: LCEL pipes. The chain returns a ReviewAnalysis directly - no manual JSON parsing.
    """
    prompt = ChatPromptTemplate.from_messages([
      ("system","You are sentiments review system. Analyze review and give sentiment, confidence, one-liner summary, themes, severity, suggested_category"),
      ("human","Review : {review}"),
    ])
    
    model = init_chat_model(provider)
    model_with_structure = model.with_structured_output(ReviewAnalysis)
    
    chain = prompt | model_with_structure
    
    return chain
    
    
    
