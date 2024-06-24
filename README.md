# articast

[![PyPI](https://img.shields.io/pypi/v/articast.svg)](https://pypi.org/project/articast/)
[![Changelog](https://img.shields.io/github/release/ivankovnatsky/articast.svg)](https://github.com/ivankovnatsky/articast/releases)
[![Tests](https://github.com/ivankovnatsky/articast/workflows/Test/badge.svg)](https://github.com/ivankovnatsky/articast/actions?query=workflow%3ATest)
[![License](https://img.shields.io/github/license/ivankovnatsky/articast)](https://github.com/ivankovnatsky/articast/blob/main/LICENSE.md)

CLI tool for converting articles to podcasts using AI Text-to-Speech APIs. I
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

Install articast with:

```console
pipx install articast
```

```console
articast --help
Usage: python -m articast [OPTIONS]

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
  --model TEXT                    The model to be used for text-to-speech
                                  conversion.
  --voice TEXT                    OpenIA voices: alloy, echo, fable, onyx,
                                  nova, shimmer; ElevenLabs voices: Nicole.
  --strip INTEGER RANGE           By what number of chars to strip the text to
                                  send to OpenAI.  [5<=x<=2000]
  --audio-format [mp3|opus|aac|flac|pcm]
                                  The audio format for the output file.
                                  Default is mp3.
  --help                          Show this message and exit.
```

```console
export OPENAI_API_KEY="your-api-key"
articast \
    --url 'https://blog.kubetools.io/kopylot-an-ai-powered-kubernetes-assistant-for-devops-developers'
```

ElevenLabs:

```console
export ELEVEN_API_KEY="your-api-key"
articast \
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
    -m articast \
    --model tts-1-hd \
    --voice nova \
    --directory . \
    --url 'https://blog.kubetools.io/kopylot-an-ai-powered-kubernetes-assistant-for-devops-developers'
```

## Testing

If you used `nix develop` all necessary dependencies should have already 
been installed, so you can just run:

```console
pytest
```

## TODO

- [ ] Bypass Cloudflare block
- [ ] Minimize costs on tests
- [ ] Add ability to render images to text and send over to text to speech as well
- [ ] Shorten filename created
- [ ] Shorten article title printed to console
- [ ] Send to device right away
- [ ] Replace print with logger
- [ ] Remove redundant warnings in pytest
- [ ] Make sure pytest shows quota errors

## Manual configurations

- OPENAI_API_KEY secret was added to repository secrets
- PYPI_TOKEN was added to release environment secrets
- Elevenlabs test do not require api key for small size requests

## Inspired by

* Long frustration of unread articles
* https://github.com/simonw/ospeak
