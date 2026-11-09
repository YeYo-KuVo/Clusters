"""Random interaction sounds and independent ambient layers on macOS."""
import hashlib
import os
from pathlib import Path
from queue import Queue
import subprocess
import sys
import tempfile
from threading import Thread


class SoundPlayer:
    def __init__(self, schedule=None, directory=None):
        self._closed = False
        self.muted = False
        self._ambience_requested = False
        self._commands = Queue()
        self._process = None
        default = Path(__file__).resolve().parents[2] / 'SOUNDS'
        self.directory = Path(directory or os.environ.get('CLUSTERS_SOUNDS_DIR', default))
        self._thread = Thread(target=self._run, daemon=True)
        if sys.platform == 'darwin':
            self._thread.start()

    def play(self, sound='button'):
        # Older callers may still use the original wood_tap/wood_tick names.
        if not self.muted:
            self._send('button')

    def celebrate(self):
        if not self.muted:
            self._send('chirp')

    def start_ambience(self):
        self._ambience_requested = True
        if not self.muted:
            self._send('start')

    def set_muted(self, muted):
        muted = bool(muted)
        if muted == self.muted:
            return
        self.muted = muted
        if muted:
            self._send('stop')
        elif self._ambience_requested:
            self._send('start')

    def _send(self, command):
        if not self._closed and sys.platform == 'darwin':
            self._commands.put(command)

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._commands.put('quit')
        if self._process is not None and self._process.poll() is None:
            try:
                self._process.terminate()
            except OSError:
                pass

    def _run(self):
        try:
            source = Path(__file__).with_name('audio_engine.swift')
            digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
            cache = Path(tempfile.gettempdir()) / f'clusters-audio-{os.getuid()}'
            cache.mkdir(exist_ok=True)
            executable = cache / f'engine-{digest}'
            if not executable.is_file():
                temporary = cache / f'build-{os.getpid()}'
                subprocess.run(
                    ['/usr/bin/swiftc', '-module-cache-path', str(cache / 'modules'),
                     str(source), '-o', str(temporary)], check=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
                )
                temporary.replace(executable)
            if self._closed:
                return
            self._process = subprocess.Popen(
                [str(executable), str(self.directory),
                 str(Path(__file__).with_name('assets') / 'sounds' / 'toucan_success.wav')], stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, text=True,
            )
            while True:
                command = self._commands.get()
                if self._process.poll() is not None:
                    break
                self._process.stdin.write(command + '\n')
                self._process.stdin.flush()
                if command == 'quit':
                    break
        except (OSError, subprocess.SubprocessError) as error:
            print(f'Clusters audio unavailable: {error}', file=sys.stderr)
        finally:
            process = self._process
            if process is not None:
                if process.stdin:
                    try:
                        process.stdin.close()
                    except OSError:
                        pass
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
