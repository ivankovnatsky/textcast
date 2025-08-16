# textcast

[![PyPI](https://img.shields.io/pypi/v/textcast.svg)](https://pypi.org/project/textcast/)
[![Changelog](https://img.shields.io/github/release/ivankovnatsky/textcast.svg)](https://github.com/ivankovnatsky/textcast/releases)
[![Tests](https://github.com/ivankovnatsky/textcast/workflows/Test/badge.svg)](https://github.com/ivankovnatsky/textcast/actions?query=workflow%3ATest)
[![License](https://img.shields.io/github/license/ivankovnatsky/textcast)](https://github.com/ivankovnatsky/textcast/blob/main/LICENSE.md)

CLI tool for converting text (articles, web content, documents) to audio using AI Text-to-Speech APIs. I
have added ElevenLabs basic functionanlity, but it's very simple, and I still
use OpenAI more for it's cheapness.

## Requirements

You need to have ffmpeg installed before running this CLI tool.

```console
brew install ffmpeg
```

Since JS based articles can't be rendered with requests we're using playwright
and chromium web driver to tackle that:

```console
pip install playwright
playwright install chromium
```

## Usage

Install textcast with:

```console
pipx install textcast
```

```console
textcast --help
Usage: python -m textcast [OPTIONS]

Options:
  --url TEXT                      URL of the article to be fetched.
  --vendor [openai|elevenlabs]    Choose vendor to use to convert text to
                                  audio.
  --file-url-list FILE            Path to a file with URLs placed on every new
                                  line.
  --file-text FILE                Path to a file with text to be sent over to
                                  AI vendor. This is currently a workaround of
                                  Cloudflare blocking.
  --directory DIRECTORY           Directory where the output audio file will
                                  be saved. The filename will be derived from
                                  the article title.
  --speech-model TEXT             The model to be used for text-to-speech
                                  conversion.
  --text-model TEXT              The model to be used for text condensing
                                  (e.g., gpt-4-turbo-preview, gpt-3.5-turbo).
  --voice TEXT                    OpenIA voices: alloy, echo, fable, onyx,
                                  nova, shimmer; ElevenLabs voices: Sarah.
  --strip INTEGER RANGE           By what number of chars to strip the text to
                                  send to OpenAI.  [5<=x<=2000]
  --audio-format [mp3|opus|aac|flac|pcm]
                                  The audio format for the output file.
                                  Default is mp3.
  --condense                      Condense the article before converting to
                                  audio.
  --condense-ratio FLOAT RANGE    Ratio to condense the text (0.2 = 20% of
                                  original length).  [0.1<=x<=1.0]
  --help                          Show this message and exit.
```

### OpenAI

```console
export OPENAI_API_KEY="your-api-key"
textcast \
    --url 'https://blog.kubetools.io/kopylot-an-ai-powered-kubernetes-assistant-for-devops-developers' \
    --speech-model tts-1-hd \
    --text-model gpt-4-turbo-preview \
    --voice nova \
    --condense \
    --condense-ratio 0.2 \
    --directory ~/Downloads/Podcasts
```

### ElevenLabs:

```console
export ELEVEN_API_KEY="your-api-key"
textcast \
  --url 'https://incident.io/blog/psychological-safety-in-incident-management' \
  --vendor elevenlabs \
  --directory ~/Downloads/Podcasts
```

## Development

If you're using Nix you can start running the tool by entering:

```console
nix develop
```

```console
export OPENAI_API_KEY="your-api-key"
python \
    -m textcast \
    --speech-model tts-1-hd \
    --text-model gpt-4-turbo-preview \
    --voice nova \
    --directory . \
    --url 'https://blog.kubetools.io/kopylot-an-ai-powered-kubernetes-assistant-for-devops-developers' \
    --condense \
    --condense-ratio 0.2
```

### Lint

I currently use these commands manually, maybe I will add some automation later on:

```console
autoflake --in-place --remove-all-unused-imports --expand-star-imports -r .
```

## Testing

If you used `nix develop` all necessary dependencies should have already 
been installed, so you can just run:

```console
pytest
```

## TODO

- [ ] Still bugs with cloudflare blocking, we need to just ignore these text and not spend money on sending them to AI
- [ ] Move failed texts to a separate file
- [ ] Add ability to use local whisper model
- [ ] Add ability to just transcribe without condensing
- [ ] In last batch of processed casts there lots of duplicated items, need to understand where that happens
- [ ] Add agentic capabilities: add a prompt to ai beforenahd to check dor context before transcribing
- [ ] Save the context db to be able to highlight some topics from last listening sessions or some new and valuable knowledge listened in new texts
- [ ] Remove gh from skipped
- [ ] Add more thorougt check on the transcribed text to verify if it does not contain a blocked page deacription, anti-bot or something

## Manual configurations

- OPENAI_API_KEY secret was added to repository secrets
- ELEVEN_API_KEY secret was added to repository secrets
- PYPI_TOKEN was added to release environment secrets

## Inspired by

* Long frustration of unread articles and text content
* https://github.com/simonw/ospeak
