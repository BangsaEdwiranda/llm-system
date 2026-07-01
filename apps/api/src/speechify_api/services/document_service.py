from sqlalchemy.orm import Session

from ..models import Document


def create_document(session: Session, owner_id: int, title: str, text: str) -> Document:
    document = Document(owner_id=owner_id, title=title, text=text)
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def list_documents_with_status(session: Session, user_id: int) -> list[dict]:
    documents = (
        session.query(Document)
        .filter(Document.owner_id == user_id)
        .order_by(Document.created_at.desc())
        .all()
    )

    results = []
    for document in documents:
        # Each access to `document.conversions` below is a separate lazy-loaded
        # query, so this loop issues one extra SELECT per document.
        latest = document.conversions[0] if document.conversions else None
        results.append(
            {
                "id": document.id,
                "title": document.title,
                "created_at": document.created_at,
                "status": latest.status if latest else "not_started",
                "audio_url": latest.audio_url if latest else None,
            }
        )
    return results


def get_document(session: Session, document_id: int) -> Document | None:
    return session.get(Document, document_id)
