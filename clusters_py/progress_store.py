"""Local completion history. Empty slots never contribute to percentages."""
import json
from math import ceil
import os
from pathlib import Path
import sys
import tempfile


def default_progress_path():
    if sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    elif sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
    return base / 'Hui Pu' / 'progress.json'


class ProgressStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else default_progress_path()
        self.completed = set()
        self.unlocked = set()
        if self.path.exists():
            data = json.loads(self.path.read_text())
            if not isinstance(data, dict) or data.get('version') != 1:
                raise ValueError('Unsupported progress file version')
            for key in ('completed', 'unlocked'):
                values = data.get(key, [])
                if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                    raise ValueError('Invalid progress file')
                setattr(self, key, set(values))

    def completed_count(self, level):
        return len(self.completed.intersection(level.puzzle_ids))

    def required_count(self, level):
        return ceil(len(level.puzzle_ids) * level.unlock_percent / 100)

    def refresh_unlocks(self, levels):
        if levels:
            self.unlocked.add(levels[0].id)
        for current, following in zip(levels, levels[1:]):
            if (current.id in self.unlocked and current.puzzle_ids
                    and self.completed_count(current) >= self.required_count(current)):
                self.unlocked.add(following.id)

    def is_playable(self, level):
        return level.id in self.unlocked and bool(level.puzzle_ids)

    def record_completion(self, puzzle_id, catalog):
        if not any(puzzle_id in level.puzzle_ids for level in catalog.levels):
            raise ValueError('Unknown puzzle completion')
        self.completed.add(puzzle_id)
        self.refresh_unlocks(catalog.levels)
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {'version': 1, 'completed': sorted(self.completed), 'unlocked': sorted(self.unlocked)}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix='progress-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(data, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
