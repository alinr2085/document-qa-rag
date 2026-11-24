from rest_framework import serializers

from .models import Document, QueryLog


class DocumentSerializer(serializers.ModelSerializer):
    chunk_count = serializers.IntegerField(source="chunks.count", read_only=True)

    class Meta:
        model = Document
        fields = ["id", "title", "file", "content", "chunk_count", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {"content": {"required": False}, "file": {"required": False}}

    def validate(self, attrs):
        if self.instance is None and not attrs.get("file") and not (attrs.get("content") or "").strip():
            raise serializers.ValidationError("یا file (docx) یا content را ارسال کنید.")
        return attrs


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField()
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20)


class SearchResultSerializer(serializers.Serializer):
    document_id = serializers.IntegerField()
    title = serializers.CharField()
    chunk_index = serializers.IntegerField()
    score = serializers.FloatField()
    text = serializers.CharField()


class AskRequestSerializer(serializers.Serializer):
    question = serializers.CharField()
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20)


class QueryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryLog
        fields = ["id", "question", "answer", "sources", "model_name", "response_time_ms", "created_at"]
        read_only_fields = fields
