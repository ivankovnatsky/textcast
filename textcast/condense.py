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
    if not text or not text.strip():
        logger.warning("Input text is empty or whitespace only")
        return text

    logger.debug(f"Input text length: {len(text)} characters")
    logger.debug(f"Target ratio: {condense_ratio} ({int(condense_ratio * 100)}%)")

    client = OpenAI()

    prompt = f"""Condense the following text while maintaining the key information.
The result should be approximately {int(condense_ratio * 100)}% of the original length:

{text}"""

    try:
        response = client.chat.completions.create(
            model=text_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        condensed_text = response.choices[0].message.content

        if not condensed_text or not condensed_text.strip():
            logger.warning("Model returned empty or whitespace-only condensed text, using original")
            return text

        logger.debug(f"Condensed text length: {len(condensed_text)} characters")
        actual_ratio = len(condensed_text) / len(text) if len(text) > 0 else 0
        logger.debug(f"Actual condensing ratio: {actual_ratio:.2f} ({int(actual_ratio * 100)}%)")

        return condensed_text

    except Exception as e:
        logger.error(f"Error during text condensing: {e}")
        logger.warning("Condensing failed, using original text")
        return text
