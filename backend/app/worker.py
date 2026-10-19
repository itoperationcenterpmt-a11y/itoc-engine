"""Proses penjadwal terpisah (satu instance), supaya API bisa jalan dengan banyak worker."""
import signal
import time
from . import jobs

if __name__ == "__main__":
    jobs.start()
    stop = {"v": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(v=True))
    try:
        while not stop["v"]:
            time.sleep(1)
    finally:
        jobs.stop()
