from speechify_api import auth
from speechify_api.models import User
from speechify_api.services import document_service


def test_create_document_for_carol(db_session):
    user = User(email="carol@example.com", hashed_password=auth.hash_password("carol-password"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    document_service.create_document(db_session, user.id, "Carol's first doc", "hello world")

    docs = document_service.list_documents_with_status(db_session, user.id)
    assert len(docs) == 1


def test_list_documents_only_returns_carols_own_document(db_session):
    # Relies on carol@example.com already existing with one document, created
    # by test_create_document_for_carol above.
    user = db_session.query(User).filter(User.email == "carol@example.com").one()
    docs = document_service.list_documents_with_status(db_session, user.id)
    assert len(docs) == 1
    assert docs[0]["title"] == "Carol's first doc"
