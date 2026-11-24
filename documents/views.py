from django.core.exceptions import ImproperlyConfigured
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import Document, QueryLog
from .serializers import (
    AskRequestSerializer,
    DocumentSerializer,
    QueryLogSerializer,
    SearchRequestSerializer,
    SearchResultSerializer,
)
from .services.rag import LLMError, answer_question, search_documents


class DocumentViewSet(viewsets.ModelViewSet):
    """CRUD for documents. Send multipart with `file` (.docx) or JSON with `content`."""

    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class SearchView(GenericAPIView):
    serializer_class = SearchRequestSerializer

    @extend_schema(responses=SearchResultSerializer(many=True))
    def post(self, request):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        docs = search_documents(s.validated_data["query"], s.validated_data.get("top_k"))
        return Response(
            [
                {
                    "document_id": d.metadata["document_id"],
                    "title": d.metadata["title"],
                    "chunk_index": d.metadata["chunk_index"],
                    "score": d.metadata["score"],
                    "text": d.page_content,
                }
                for d in docs
            ]
        )


class AskView(GenericAPIView):
    serializer_class = AskRequestSerializer

    @extend_schema(responses=QueryLogSerializer)
    def post(self, request):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        question = s.validated_data["question"]
        try:
            result = answer_question(question, s.validated_data.get("top_k"))
        except ImproperlyConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except LLMError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        log = QueryLog.objects.create(question=question, **result)
        return Response(QueryLogSerializer(log).data, status=status.HTTP_201_CREATED)


class HistoryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """History of questions and answers."""

    queryset = QueryLog.objects.all()
    serializer_class = QueryLogSerializer
