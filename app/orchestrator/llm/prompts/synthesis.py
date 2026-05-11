SYNTHESIS_SYSTEM_PROMPT = """You are an expert technical synthesizer.
Your goal is to synthesize the provided context into a highly concise, accurate final response for the user.

CONSTRAINTS:
1. Be concise. Do not use filler words.
2. If the user's query cannot be answered using the provided context, state that clearly.
3. Incorporate any critique feedback from previous iterations explicitly.
4. Output cleanly formatted Markdown.
"""

def build_synthesis_messages(user_input: str, retrieved_context: str, critique_feedback: str) -> list:
    content = f"USER QUERY:\n{user_input}\n\n"
    if retrieved_context:
        content += f"RETRIEVED CONTEXT:\n{retrieved_context}\n\n"
    if critique_feedback:
        content += f"CRITIQUE FEEDBACK TO INCORPORATE:\n{critique_feedback}\n\n"
        
    return [
        {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
        {"role": "user", "content": content}
    ]
