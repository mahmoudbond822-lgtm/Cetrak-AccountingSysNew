from rest_framework.routers import DefaultRouter

from apps.purchases import views

router = DefaultRouter()
router.register(r"vendors", views.VendorViewSet, basename="vendor")
router.register(r"invoices", views.PurchaseInvoiceViewSet, basename="purchase-invoice")
router.register(r"payments", views.PurchasePaymentViewSet, basename="purchase-payment")
router.register(r"settings", views.PurchaseSettingsViewSet, basename="purchase-settings")

urlpatterns = router.urls