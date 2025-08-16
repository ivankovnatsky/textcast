import logging

logger = logging.getLogger(__name__)


def generate_unique_filename(output_path):
    logger.debug(f"Generating unique filename for base path: {output_path}")
    base = output_path.stem
    suffix = output_path.suffix
    directory = output_path.parent
    counter = 1
    new_path = output_path

    logger.debug(f"Initial path: {new_path}")

    while new_path.exists():
        logger.debug(f"Path {new_path} already exists, incrementing counter")
        new_path = directory / f"{base}_{counter}{suffix}"
        counter += 1
        logger.debug(f"Trying new path: {new_path}")

    logger.info(f"Generated unique filename: {new_path}")
    return new_path
