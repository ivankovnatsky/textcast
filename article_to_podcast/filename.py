def generate_unique_filename(output_path):
    base = output_path.stem
    suffix = output_path.suffix
    directory = output_path.parent

    counter = 1
    new_path = output_path
    while new_path.exists():
        new_path = directory / f"{base}_{counter}{suffix}"
        counter += 1

    return new_path
