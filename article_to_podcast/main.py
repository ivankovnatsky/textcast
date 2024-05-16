import io
from pathlib import Path
from openai import OpenAI
from pydub import AudioSegment
from .chunks import split_text
from .filename import generate_unique_filename


SILINCE_TIME_MS = 3000


def process_article(text, filename, model, voice):
    client = OpenAI()
    chunks = split_text(text)

    output_path = Path(filename)
    output_format = output_path.suffix.lstrip(".")

    # Generate a unique filename if the file already exists
    if output_path.exists():
        output_path = generate_unique_filename(output_path)

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
        # Add a silence at the start and end of audio file
        silence = AudioSegment.silent(duration=SILINCE_TIME_MS)
        combined_audio = silence + combined_audio + silence

        combined_audio.export(output_path, format=output_format)
        print(f"Audio saved to {output_path}")
    else:
        print("No audio generated due to errors.")
        if output_path.exists():
            output_path.unlink()  # Ensure no partial files are left
