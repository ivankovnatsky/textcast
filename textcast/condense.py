from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

def condense_text(text: str, text_model: str, condense_ratio: float) -> str:
    """
    Condense the text using OpenAI's GPT model while maintaining key information.
    
    Args:
        text: The text to condense
        text_model: The OpenAI model to use for condensing
        condense_ratio: Target length as a ratio of original length
    
    Returns:
        str: Condensed version of the input text
    """
    client = OpenAI()
    
    prompt = f"""Condense the following text while maintaining the key information. 
The result should be approximately {int(condense_ratio * 100)}% of the original length:

{text}"""

    response = client.chat.completions.create(
        model=text_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    
    return response.choices[0].message.content
