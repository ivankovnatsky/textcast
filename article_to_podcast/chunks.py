# * OpenIA limit in chars for one request is 4096.
# * For ElevenLabs it's 2500 for non subscribed users and 5000 for
# subscribed ones.
#
# Thus, let's set common limit to 2500
TEXT_SEND_LIMIT = 2500


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
