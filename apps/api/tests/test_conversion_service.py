from speechify_api.models import Document, User
from speechify_api.services import conversion_service


def test_create_conversion_marks_completed_on_success(db_session, monkeypatch):
    # Force the simulated TTS engine down the success path so this test is
    # deterministic regardless of conversion_service's built-in failure rate.
    monkeypatch.setattr(conversion_service.random, "random", lambda: 0.9)

    user = User(email="dave@example.com", hashed_password="unused-in-this-test")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    document = Document(owner_id=user.id, title="Dave's doc", text="a short piece of text")
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    conversion = conversion_service.create_conversion(db_session, document.id, document.text)

    assert conversion.status == "completed"
    assert conversion.audio_url is not None
