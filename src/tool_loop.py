from dotenv import load_dotenv
from google import genai
from google.genai import types

from .tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

load_dotenv()

client = genai.Client()

SYSTEM_PROMPT = """You are a customer support triage agent for ReviewGuard. Given a customer
review, resolve it using the tools available to you:

- search_knowledge_base: find the relevant policy/resolution guidance before drafting any answer.
- lookup_order: check a specific order's status if the customer mentions an order ID.
- escalate_ticket: escalate to a human only if you cannot resolve the issue yourself - not for
  routine issues the knowledge base already covers.

Ground your final resolution in what the knowledge base actually says - do not invent policy.
When you have enough information to respond, reply with a final plain-text resolution for the
customer and do not call any more tools.
"""


def _build_tool() -> types.Tool:
    return types.Tool(
        functionDeclarations=[
            types.FunctionDeclaration(
                name=schema["name"],
                description=schema["description"],
                parametersJsonSchema=schema["parameters"],
            )
            for schema in TOOL_SCHEMAS
        ]
    )


def run_tool_loop(review: str, max_steps: int = 6) -> str:
    """
    Hand-written agent loop, no framework:
      1. Send review + tool schemas to the model.
      2. If the response is a tool call: run the real function, append the result, loop.
      3. If it's a final text answer: return it.
      4. Stop at max_steps to guard against infinite loops.
    """
    tool = _build_tool()
    config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, tools=[tool])
    contents = [types.Content(role="user", parts=[types.Part(text=review)])]

    for step in range(max_steps):
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=contents,
            config=config,
        )

        candidate_content = response.candidates[0].content
        contents.append(candidate_content)

        function_calls = [p.function_call for p in candidate_content.parts if p.function_call]

        if not function_calls:
            text_parts = [p.text for p in candidate_content.parts if p.text]
            return "".join(text_parts)

        response_parts = []
        for fc in function_calls:
            func = TOOL_FUNCTIONS.get(fc.name)
            if func is None:
                result = f"Unknown tool: {fc.name}"
            else:
                try:
                    result = func(**dict(fc.args))
                except Exception as e:
                    result = f"Tool {fc.name} raised an error: {e}"

            response_parts.append(
                types.Part.from_function_response(name=fc.name, response={"result": result})
            )

        contents.append(types.Content(role="user", parts=response_parts))

    return "Reached max_steps without a final answer - stopping to avoid an infinite loop."
