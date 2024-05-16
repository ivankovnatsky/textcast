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
