from rest_framework.routers import DefaultRouter

from apps.sales import views

router = DefaultRouter()
router.register(r"customers", views.CustomerViewSet, basename="customer")
router.register(r"invoices", views.SalesInvoiceViewSet, basename="invoice")
router.register(r"payments", views.PaymentViewSet, basename="payment")
router.register(r"settings", views.SalesSettingsViewSet, basename="sales-settings")

urlpatterns = router.urls