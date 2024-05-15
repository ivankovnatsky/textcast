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
    client = OpenAI()
    chunks = split_text(text)

    output_path = Path(filename)
    output_format = output_path.suffix.lstrip(".")

    combined_audio = AudioSegment.empty()
    success = True

    for i, chunk in enumerate(chunks, start=1):
        try:
            response = client.audio.speech.create(model=model, voice=voice, input=chunk)
            part_audio = AudioSegment.from_file(
                io.BytesIO(response.content), format=output_format
            )
            combined_audio += part_audio
        except Exception as e:
            print(f"An error occurred for part {i}: {e}")
            import traceback

            traceback.print_exception(type(e), e, e.__traceback__)
            if "429" in str(e):
                print("Quota exceeded. Stopping further requests.")
                success = False
                break

    if success and not combined_audio.empty():
        combined_audio.export(output_path, format=output_format)
        print(f"Combined audio saved to {output_path}")
    else:
        print("No audio generated due to errors.")
        if output_path.exists():
            output_path.unlink()  # Ensure no partial files are left
