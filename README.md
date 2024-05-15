# Article to Podcast

[![PyPI](https://img.shields.io/pypi/v/article-to-podcast.svg)](https://pypi.org/project/article-to-podcast/)
[![Changelog](https://img.shields.io/github/release/ivankovnatsky/article-to-podcast.svg)](https://github.com/ivankovnatsky/article-to-podcast/releases)
[![Tests](https://github.com/ivankovnatsky/article-to-podcast/workflows/Test/badge.svg)](https://github.com/ivankovnatsky/article-to-podcast/actions?query=workflow%3ATest)
[![License](https://img.shields.io/github/license/ivankovnatsky/article-to-podcast)](https://github.com/ivankovnatsky/article-to-podcast/blob/main/LICENSE.md)

CLI tool for converting articles to podcasts using OpenAI's Text-to-Speech API.

## Requirements

You need to have ffmpeg installed before running this CLI tool.

## Usage

Install article-to-podcast with:

```console
pipx install article-to-podcast
```

```console
article-to-podcast --help                                                                                                                   
Usage: article-to-podcast [OPTIONS]

Options:
  --url TEXT                      URL of the article to be fetched.
                                  [required]
  --directory DIRECTORY           Directory where the output audio file will
                                  be saved. The filename will be derived from
                                  the article title.  [required]
  --audio-format [mp3|opus|aac|flac|pcm]
                                  The audio format for the output file.
                                  Default is mp3.
  --model [tts-1|tts-1-hd]        The model to be used for text-to-speech
                                  conversion.
  --voice [alloy|echo|fable|onyx|nova|shimmer]
                                  The voice to be used for the text-to-speech
                                  conversion. Voice options: alloy:   A
                                  balanced and neutral voice. echo:    A more
                                  dynamic and engaging voice. fable:   A
                                  narrative and storytelling voice. onyx:    A
                                  deep and resonant voice. nova:    A bright
                                  and energetic voice. shimmer: A soft and
                                  soothing voice. Experiment with different
                                  voices to find one that matches your desired
                                  tone and audience. The current voices are
                                  optimized for English.
  --help                          Show this message and exit.
```

```console
export OPENAI_API_KEY="your-api-key"
article-to-podcast \
    --url 'https://blog.kubetools.io/kopylot-an-ai-powered-kubernetes-assistant-for-devops-developers'
```

## Development

If you're using Nix you can start running the tool by entering:

```console
nix develop
```

```console
export OPENAI_API_KEY="your-api-key"
python \
    -m article_to_podcast \
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

- [x] Automatically fetch filename to save article from the article name
- [ ] Work around: "Enable cookies and javascript to continue" errors
- [ ] Remove redundant warnings in pytest
- [ ] Make sure pytest shows quota errors

## Disclaimer

Code is almost exclusively written by GPT-4 and GPT-4o models.

## Inspired by

* Long frustration of unread articles
* https://github.com/simonw/ospeak
