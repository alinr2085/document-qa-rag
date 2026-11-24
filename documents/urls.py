from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AskView, DocumentViewSet, HistoryViewSet, SearchView

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")
router.register("history", HistoryViewSet, basename="history")

urlpatterns = [
    path("search/", SearchView.as_view(), name="search"),
    path("ask/", AskView.as_view(), name="ask"),
    path("", include(router.urls)),
]
