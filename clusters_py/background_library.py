"""Choose one saved original per game, avoiding consecutive repeats."""
import hashlib
from pathlib import Path
import random
import tempfile

BACKGROUND_DIRECTORY = Path(__file__).with_name('assets') / 'backgrounds'
_last_background = None


def choose_background(directory=BACKGROUND_DIRECTORY, rng=None, history_path=None):
    global _last_background
    directory = Path(directory)
    files = sorted(directory.glob('*.png'))
    if not files:
        raise FileNotFoundError(f'No background images found in {directory}')
    if history_path is None:
        key = hashlib.sha256(str(directory.resolve()).encode()).hexdigest()[:12]
        history_path = Path(tempfile.gettempdir()) / f'clusters-background-{key}.txt'
    history_path = Path(history_path)
    previous = _last_background
    try:
        previous = history_path.read_text().strip()
    except OSError:
        pass
    choices = [file for file in files if file.name != previous] or files
    chosen = (rng or random).choice(choices)
    _last_background = chosen.name
    try:
        history_path.write_text(chosen.name)
    except OSError:
        pass
    return chosen
