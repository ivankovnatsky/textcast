import logging

from openai import OpenAI

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

    input_word_count = len(text.split())
    target_word_count = int(input_word_count * condense_ratio)

    logger.debug(f"Input text length: {len(text)} characters, {input_word_count} words")
    logger.debug(
        f"Target ratio: {condense_ratio} ({int(condense_ratio * 100)}%), "
        f"target word count: {target_word_count}"
    )

    client = OpenAI()

    system_message = f"""You are a text condensing assistant. Your task is to shorten text while preserving key information.

CRITICAL REQUIREMENTS:

1. You MUST produce output that is approximately {target_word_count} words
   long. This word count requirement is non-negotiable. If you produce
   significantly fewer words, you have failed the task.
2. You MUST write the output in the SAME LANGUAGE as the input text."""

    prompt = f"""Condense the following text.

LENGTH REQUIREMENT (MANDATORY):

- Original text: {input_word_count} words
- Required output length: {target_word_count} words (±10%)
- Count your words carefully. Your response MUST be between {int(target_word_count * 0.9)} and {int(target_word_count * 1.1)} words.

LANGUAGE REQUIREMENT (MANDATORY):

- Output MUST be in the same language as the input text
- Do NOT translate, keep in the original language

Guidelines:

- Try to stick to the original text, try to not paraphrase
- Preserve all key facts, arguments, and important details
- Shorten sentences but keep all main points
- Remove only truly redundant content

Text to condense:

{text}"""

    try:
        response = client.chat.completions.create(
            model=text_model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        condensed_text = response.choices[0].message.content

        if not condensed_text or not condensed_text.strip():
            logger.warning(
                "Model returned empty or whitespace-only condensed text, using original"
            )
            return text

        output_word_count = len(condensed_text.split())
        actual_ratio = output_word_count / input_word_count if input_word_count > 0 else 0
        ratio_deviation = abs(actual_ratio - condense_ratio)

        logger.debug(
            f"Condensed text length: {len(condensed_text)} characters, {output_word_count} words"
        )
        logger.info(
            f"Condense result: {input_word_count} -> {output_word_count} words "
            f"(target: {target_word_count}, actual ratio: {actual_ratio:.1%}, "
            f"deviation: {ratio_deviation:.1%})"
        )

        if ratio_deviation > 0.20:
            logger.warning(
                f"Condensed output deviated significantly from target: "
                f"got {actual_ratio:.1%}, wanted {condense_ratio:.1%}"
            )

        return condensed_text

    except Exception as e:
        logger.error(f"Error during text condensing: {e}")
        logger.warning("Condensing failed, using original text")
        return text
