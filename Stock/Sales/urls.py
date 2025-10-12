from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    CategoryViewSet, SubCategoryViewSet,
    SupplierViewSet, CustomerViewSet,
    ProductViewSet, StockEntryViewSet,
    MonthlyOpeningStockViewSet,
    InvoiceViewSet, InvoiceItemViewSet,
    PaymentViewSet, LPOViewSet,
    AuditLogViewSet, DashboardViewSet
)

# Create a router and register viewsets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'subcategories', SubCategoryViewSet, basename='subcategory')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'stock-entries', StockEntryViewSet, basename='stockentry')
router.register(r'monthly-opening-stock', MonthlyOpeningStockViewSet, basename='monthlyopeningstock')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'invoice-items', InvoiceItemViewSet, basename='invoiceitem')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'lpos', LPOViewSet, basename='lpo')
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

app_name = 'inventory'

urlpatterns = [
    path('', include(router.urls)),
]