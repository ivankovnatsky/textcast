import sys
import os
from elevenlabs.client import ElevenLabs
from elevenlabs import save

ELEVEN_TEXT_LIMIT_NONSIGNED=500

def process_article_elevenlabs(text, filename, model, voice):
    try:
        api_key = os.environ['ELEVEN_API_KEY']
        client = ElevenLabs(api_key=api_key)
    except:
        print("Will try to use EleveLabs without API key.")

        if len(text) > ELEVEN_TEXT_LIMIT_NONSIGNED:
            print(f"""
This request's text has {len(text)} characters and exceeds the character limit
of 500 characters for non signed in accounts.
"""
            )
            sys.exit(0)
        else:
            client = ElevenLabs()

    audio = client.generate(
      text=text,
      voice=voice,
      model=model
    )

    save(audio, filename)
