"""Background job runner. Bridges the SYNC, blocking engine to the async HTTP layer:
each build runs in a daemon thread, progress events land in a thread-safe queue the SSE
endpoint drains, and the final result / friendly error is recorded on the Job."""
from __future__ import annotations
import queue
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional
from engine.errors import FilingForgeError

JOB_DONE_SENTINEL = object()   # pushed to events when a job ends (success or error)

ProgressFn = Callable[[dict], None]
WorkFn = Callable[[ProgressFn], dict]


@dataclass
class Job:
    id: str
    status: str = "queued"                 # queued | running | done | cancelled | error
    events: "queue.Queue" = field(default_factory=queue.Queue)
    result: Optional[dict] = None
    error: Optional[str] = None            # friendly user_message
    last_progress: Optional[dict] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self) -> Job:
        job = Job(id=uuid.uuid4().hex)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        """Signal a running job to stop. Returns False for an unknown job. The engine loop
        polls job.cancel_event via should_cancel and exits cleanly (library stays consistent)."""
        job = self.get(job_id)
        if job is None:
            return False
        job.cancel_event.set()
        return True

    def start(self, job: Job, work: WorkFn) -> None:
        def runner() -> None:
            job.status = "running"

            def on_progress(ev: dict) -> None:
                job.last_progress = ev
                job.events.put(ev)

            try:
                job.result = work(on_progress)
                job.status = "cancelled" if (job.result or {}).get("cancelled") else "done"
            except FilingForgeError as e:
                job.error = e.user_message
                job.status = "error"
            except Exception:
                job.error = "Something went wrong while building the library. Please try again."
                job.status = "error"
            finally:
                job.events.put(JOB_DONE_SENTINEL)

        threading.Thread(target=runner, name=f"build-{job.id}", daemon=True).start()


def run_build(scrip_code: str, ticker: str, dest: str, everything: bool, categories: list[str],
              years: int, should_cancel: Optional[Callable[[], bool]] = None) -> WorkFn:
    """Return a WorkFn that performs the real engine build. Imported lazily so tests that
    monkeypatch this never construct a real BSEClient. The returned closure is what the
    JobManager runs in its thread. `should_cancel` (the job's cancel_event.is_set) lets a
    Stop request break the download loop cleanly."""
    from engine.bse_client import BSEClient
    from engine.library import build_library
    from engine.models import CURATED_BY_KEY
    from engine.progress import ProgressEvent

    specs = [CURATED_BY_KEY[k] for k in categories]

    def work(on_progress: ProgressFn) -> dict:
        client = BSEClient()
        try:
            def bridge(ev: ProgressEvent) -> None:
                on_progress({"stage": ev.stage, "current": ev.current, "total": ev.total,
                             "message": ev.message, "percent": ev.percent})
            res = build_library(scrip_code, ticker, Path(dest).expanduser(), specs, years, client,
                                on_progress=bridge, everything=everything, should_cancel=should_cancel)
            return {"downloaded": len(res.downloaded), "skipped": len(res.skipped),
                    "failed": len(res.failed),
                    "ready": res.ready,
                    "pending": [asdict(item) for item in res.pending],
                    "cancelled": res.cancelled}
        finally:
            client.close()

    return work
