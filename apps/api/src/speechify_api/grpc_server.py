from concurrent import futures

import grpc

from . import auth
from .db import SessionLocal, init_db
from .models import User
from .proto import speechify_pb2, speechify_pb2_grpc
from .services import document_service


def _current_user(session, access_token: str) -> User:
    user_id = auth.decode_access_token(access_token)
    user = session.get(User, user_id)
    if user is None:
        raise ValueError("invalid token")
    return user


class SpeechifyServicer(speechify_pb2_grpc.SpeechifyServiceServicer):
    def Login(self, request, context):
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.email == request.email).first()
            if user is None or not auth.verify_password(request.password, user.hashed_password):
                context.abort(grpc.StatusCode.UNAUTHENTICATED, "invalid credentials")
            return speechify_pb2.TokenResponse(access_token=auth.create_access_token(user.id))
        finally:
            session.close()

    def CreateDocument(self, request, context):
        session = SessionLocal()
        try:
            user = _current_user(session, request.access_token)
            document = document_service.create_document(session, user.id, request.title, request.text)
            return speechify_pb2.DocumentDetail(
                id=document.id, owner_id=document.owner_id, title=document.title, text=document.text
            )
        finally:
            session.close()

    def ListDocuments(self, request, context):
        session = SessionLocal()
        try:
            user = _current_user(session, request.access_token)
            rows = document_service.list_documents_with_status(session, user.id)
            return speechify_pb2.ListDocumentsResponse(
                documents=[
                    speechify_pb2.DocumentSummary(
                        id=row["id"],
                        title=row["title"],
                        status=row["status"],
                        audio_url=row["audio_url"] or "",
                    )
                    for row in rows
                ]
            )
        finally:
            session.close()

    def GetDocument(self, request, context):
        session = SessionLocal()
        try:
            _current_user(session, request.access_token)
            document = document_service.get_document(session, request.document_id)
            if document is None:
                context.abort(grpc.StatusCode.NOT_FOUND, "document not found")
            return speechify_pb2.DocumentDetail(
                id=document.id, owner_id=document.owner_id, title=document.title, text=document.text
            )
        finally:
            session.close()


def serve(port: int = 50051) -> grpc.Server:
    init_db()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    speechify_pb2_grpc.add_SpeechifyServiceServicer_to_server(SpeechifyServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    return server


if __name__ == "__main__":
    grpc_server = serve()
    grpc_server.wait_for_termination()
