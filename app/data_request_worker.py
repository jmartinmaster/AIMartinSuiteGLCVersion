# Production Logging Center (GLC Edition)
# Copyright (C) 2026 Jamie Martin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import queue
import threading

__module_name__ = "Data Request Worker"
__version__ = "1.0.0"


class DataRequestWorker:
    def __init__(self, schedule_callback, exception_logger=None):
        self.schedule_callback = schedule_callback
        self.exception_logger = exception_logger
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, name="DataRequestWorker", daemon=True)
        self._thread.start()

    def stop(self):
        thread = self._thread
        if thread is None:
            return
        self._stop_event.set()
        self._queue.put(None)
        if thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.5)
        self._thread = None

    def submit(self, request_callable, on_success=None, on_error=None, description="data_request"):
        if not callable(request_callable):
            raise TypeError("request_callable must be callable")
        self._queue.put((request_callable, on_success, on_error, description))

    def _schedule(self, callback):
        if callable(callback):
            self.schedule_callback(callback)

    def _worker(self):
        while not self._stop_event.is_set():
            try:
                request = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue
            if request is None:
                continue

            request_callable, on_success, on_error, description = request
            try:
                result = request_callable()
            except Exception as exc:
                if callable(on_error):
                    self._schedule(lambda callback=on_error, error=exc: callback(error))
                elif callable(self.exception_logger):
                    self.exception_logger(description, exc)
                continue

            if callable(on_success):
                self._schedule(lambda callback=on_success, value=result: callback(value))