from .models import SentimentResult
# Anthropic: from anthropic import Anthropic
from google import genai
import os
from dotenv import load_dotenv
from pydantic import ValidationError

load_dotenv()

# Anthropic: client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

def build_prompt(review: str) -> str:
    """Return a prompt that (1) states the task, (2) shows the EXACT JSON shape
    matching SentimentResult, (3) says 'respond with ONLY valid JSON, no code fences'.
    TODO: write this. A vague prompt is the #1 cause of malformed output. This is 60% of the work.
    """
    prompt = f"""Classify the sentiment of this customer review.

Allowed sentiment values: "positive", "neutral", or "negative" - pick exactly one.
Confidence is a float between 0 and 1 representing how sure you are.
key_issues is a list of concrete problems the customer named - use an empty list if none were mentioned.
summary is a one-sentence summary of the review.

Respond with ONLY a JSON object in exactly this shape, no markdown, no code fences, no extra text:
{{"sentiment": "positive", "confidence": 0.85, "key_issues": ["late delivery"], "summary": "Customer is happy but shipping was slow."}}

Review: {review}
"""
    return prompt


def estimate_cost(review: str) -> float:
    """Rough input-token count x price-per-token. TODO: count tokens, multiply, return dollars.
    Concept: you should be able to guess a call's cost before making it.
    """
    count = len(build_prompt(review))
    tokens: float = count/4
    # Anthropic: considering 3$ per 1 million input tokens (Claude Sonnet)
    # Gemini free tier (gemini-2.0-flash) is $0 - update this if you move to a paid tier
    return tokens * 0/1000000


def classify_sentiment(review: str, max_retries: int = 1) -> SentimentResult:
    """
    TODO implement, in order:
      1. Call the raw API (anthropic.messages.create) with build_prompt(review).
      2. Pull out the text content.
      3. SentimentResult.model_validate_json(text)  -> return on success.
      4. On ValidationError: append the error text to the prompt and retry, telling the model
         exactly what was wrong. THIS retry pattern reappears every day this week - internalize it.
    """
    prompt = build_prompt(review)
    for attempt in range(max_retries + 1):
        # Anthropic:
        # response = client.messages.create(
        #         model="claude-sonnet-4-5-20250929",
        #         max_tokens = 512,
        #         temperature = 0,
        #         messages = [
        #             {
        #                 "role": "user",
        #                 "content": prompt
        #             }
        #         ]
        #     )
        # Anthropic: text = response.content[0].text
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        try:
            return SentimentResult.model_validate_json(response.text)
        except ValidationError as e:
            prompt = f"{prompt}\n\nYour last response failed validation: {e}\nFix it and respond with ONLY corrected JSON"
    raise ValueError(f"Failed to get valid response after {max_retries} retries")        


def stream_explanation(review: str) -> None:
    """Separate call that STREAMS a human-readable explanation token-by-token to the terminal.
    TODO: use the streaming API and print chunks as they arrive.
    """
    prompt = f"Explain in plain, conversational language why this customer review would be classified with a particular sentiment:\n\n{review}"
    # Anthropic:
    # with client.messages.stream(
    #     model = "claude-sonnet-4-5-20250929",
    #     max_tokens=512,
    #     temperature=0,
    #     messages=[
    #         {
    #             "role":"user",
    #             "content":prompt
    #         }
    #     ]
    # ) as stream:
    #     for text in stream.text_stream:
    #         print(text, end = "", flush = True)
    for chunk in client.models.generate_content_stream(
        model="gemini-2.0-flash",
        contents=prompt,
    ):
        print(chunk.text, end="", flush=True)

    print()
