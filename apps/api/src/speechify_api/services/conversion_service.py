import random
import time

from sqlalchemy.orm import Session

from ..models import Conversion

# In-memory job progress, keyed by conversion id. Read by the polling endpoint.
_JOB_PROGRESS: dict[str, int] = {}


def get_job_progress(job_id: str) -> int:
    return _JOB_PROGRESS.get(job_id, 0)


def _run_tts_engine(job_id: str, text: str) -> str:
    """Simulate a call to an external TTS engine, reporting progress as it goes.

    Occasionally raises to simulate a real engine timing out or erroring.
    """
    chunks = max(1, len(text) // 20)
    _JOB_PROGRESS[job_id] = 0
    for _ in range(chunks):
        time.sleep(0.02)
        _JOB_PROGRESS[job_id] = _JOB_PROGRESS.get(job_id, 0) + (100 // chunks)

    if random.random() < 0.2:
        raise RuntimeError("TTS engine timed out")

    return f"https://audio.example.com/{abs(hash(text)) % 10**8}.mp3"


def create_conversion(session: Session, document_id: int, text: str) -> Conversion:
    conversion = Conversion(document_id=document_id, status="processing")
    session.add(conversion)
    session.commit()
    session.refresh(conversion)

    job_id = str(conversion.id)
    try:
        audio_url = _run_tts_engine(job_id, text)
    except RuntimeError:
        # See FINDINGS.md: "Unhandled TTS failure leaves conversion stuck at processing".
        conversion.status = "failed"
        session.commit()
        session.refresh(conversion)
        return conversion

    conversion.status = "completed"
    conversion.audio_url = audio_url
    session.commit()
    session.refresh(conversion)
    return conversion
