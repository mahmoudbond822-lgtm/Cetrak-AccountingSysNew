from rest_framework.routers import DefaultRouter

from apps.inventory import views

router = DefaultRouter()
router.register(r"products", views.ProductViewSet, basename="product")
router.register(r"warehouses", views.WarehouseViewSet, basename="warehouse")
router.register(
    r"stock-balances", views.StockBalanceViewSet, basename="stock-balance"
)
router.register(
    r"stock-movements", views.StockMovementViewSet, basename="stock-movement"
)
router.register(r"adjustments", views.StockAdjustmentViewSet, basename="adjustment")
router.register(r"settings", views.InventorySettingsViewSet, basename="inventory-settings")

urlpatterns = router.urls