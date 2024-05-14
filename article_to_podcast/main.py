import io
from pathlib import Path
from openai import OpenAI
from pydub import AudioSegment

TEXT_SEND_LIMIT = 4096  # Constant for the text limit


def split_text(text, limit=TEXT_SEND_LIMIT):
    words = text.split()
    chunks = []
    current_chunk = words[0]

    for word in words[1:]:
        if len(current_chunk) + len(word) + 1 <= limit:
            current_chunk += " " + word
        else:
            chunks.append(current_chunk)
            current_chunk = word
    chunks.append(current_chunk)

    return chunks


def process_article(text, filename, model, voice):
    chunks = split_text(text)

    output_path = Path(filename)
    if not output_path.suffix:
        output_path = output_path.with_suffix(".mp3")

    output_format = output_path.suffix.lstrip(".")

    combined_audio = AudioSegment.empty()

    for i, chunk in enumerate(chunks, start=1):
        try:
            client = OpenAI()
            response = client.audio.speech.create(model=model, voice=voice, input=chunk)
            part_audio = AudioSegment.from_file(
                io.BytesIO(response.content), format="mp3"
            )
            combined_audio += part_audio
        except Exception as e:
            print(f"An error occurred for part {i}: {e}")

    combined_audio.export(output_path, format=output_format)
    print(f"Combined audio saved to {output_path}")
