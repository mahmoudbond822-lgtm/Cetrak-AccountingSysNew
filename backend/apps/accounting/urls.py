from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.accounting.views import AccountViewSet, JournalEntryViewSet, LedgerViewSet, ReportViewSet

router = DefaultRouter()
router.register(r"accounts", AccountViewSet, basename="account")
router.register(r"journal-entries", JournalEntryViewSet, basename="journalentry")
router.register(r"ledger", LedgerViewSet, basename="ledger")
router.register(r"reports", ReportViewSet, basename="report")

urlpatterns = [
    path("", include(router.urls)),
]
