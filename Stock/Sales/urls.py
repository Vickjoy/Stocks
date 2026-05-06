# urls.py
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from .views import (
    CustomTokenObtainPairView, UserViewSet,
    CategoryViewSet, SubCategoryViewSet, SubSubCategoryViewSet, ProductGroupViewSet,
    SupplierViewSet, CustomerViewSet,
    ProductViewSet, StockEntryViewSet, StockMovementViewSet,
    MonthlyOpeningStockViewSet,
    AuditLogViewSet, DashboardViewSet,
    SaleViewSet, StockDiscrepancyViewSet,
    password_reset_request,
    password_reset_confirm,
    password_reset_validate,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'subcategories', SubCategoryViewSet, basename='subcategory')
router.register(r'subsubcategories', SubSubCategoryViewSet, basename='subsubcategory')
router.register(r'groups', ProductGroupViewSet, basename='productgroup')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'stock-entries', StockEntryViewSet, basename='stockentry')
router.register(r'monthly-opening-stock', MonthlyOpeningStockViewSet, basename='monthlyopeningstock')
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'sales', SaleViewSet, basename='sale')
router.register(r'stock-movements', StockMovementViewSet, basename='stockmovement')
router.register(r'reports/stock-discrepancy', StockDiscrepancyViewSet, basename='stockdiscrepancy')

app_name = 'inventory'

urlpatterns = [
    path('', include(router.urls)),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password-reset/', password_reset_request, name='password_reset_request'),
    path('password-reset/confirm/', password_reset_confirm, name='password_reset_confirm'),
    path('password-reset/validate/<str:uid>/<str:token>/', password_reset_validate, name='password_reset_validate'),
]