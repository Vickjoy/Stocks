# views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, DecimalField, F
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User

from .models import (
    Category, SubCategory, SubSubCategory, ProductGroup, Supplier, Customer, Product,
    MonthlyOpeningStock, StockEntry, AuditLog, Sale, SaleLineItem
)
from .serializers import (
    UserSerializer, UserDetailSerializer,
    CategorySerializer, SubCategorySerializer, SubSubCategorySerializer, ProductGroupSerializer,
    SupplierSerializer, CustomerSerializer,
    ProductSerializer, ProductDetailSerializer,
    StockEntrySerializer, MonthlyOpeningStockSerializer,
    AuditLogSerializer, DashboardSummarySerializer, SaleSerializer, SaleCreateSerializer
)


# ========================
# User ViewSet
# ========================
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'date_joined']
    ordering = ['-date_joined']
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


# ========================
# Category ViewSet
# ========================
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.prefetch_related(
        'subcategories__subsubcategories'
    ).all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [SearchFilter]
    search_fields = ['name']


# ========================
# SubCategory ViewSet
# ========================
class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.select_related('category').prefetch_related('subsubcategories')
    serializer_class = SubCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['category']
    search_fields = ['name']


# ========================
# SubSubCategory ViewSet
# ========================
class SubSubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubSubCategory.objects.select_related('subcategory__category')
    serializer_class = SubSubCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subcategory', 'subcategory__category']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


# ========================
# ProductGroup ViewSet (Deprecated)
# ========================
class ProductGroupViewSet(viewsets.ModelViewSet):
    queryset = ProductGroup.objects.select_related('subcategory__category').prefetch_related('products')
    serializer_class = ProductGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subcategory', 'subcategory__category']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


# ========================
# Supplier ViewSet
# ========================
class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['company_name', 'phone']
    ordering_fields = ['company_name', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        supplier = self.get_object()
        supplier.is_active = not supplier.is_active
        supplier.save()
        return Response({'is_active': supplier.is_active})


# ========================
# Customer ViewSet
# ========================
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['company_name', 'phone']
    ordering_fields = ['company_name', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        customer = self.get_object()
        customer.is_active = not customer.is_active
        customer.save()
        return Response({'is_active': customer.is_active})


# ========================
# Product ViewSet
# ========================
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related(
        'category',
        'subcategory__category',
        'subsubcategory__subcategory',
        'group'
    )
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'subcategory', 'subsubcategory', 'group', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['code', 'current_stock', 'unit_price', 'created_at']
    ordering = ['code']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSerializer
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        products = self.queryset.filter(current_stock__lte=F('minimum_stock'))
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        product = self.get_object()
        quantity = int(request.data.get('quantity', 0))
        entry_type = request.data.get('type', 'Adjustment')
        notes = request.data.get('notes', '')
        supplier_id = request.data.get('supplier', None)
        
        if quantity <= 0:
            return Response(
                {'error': 'Quantity must be greater than 0'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        supplier = None
        if supplier_id:
            try:
                supplier = Supplier.objects.get(id=supplier_id, is_active=True)
            except Supplier.DoesNotExist:
                return Response(
                    {'error': 'Invalid supplier selected'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if entry_type == 'In':
            product.current_stock += quantity
            if not notes:
                notes = f'Stock replenishment - {quantity} units added'
                if supplier:
                    notes += f' from {supplier.company_name}'
        elif entry_type == 'Out':
            if product.current_stock < quantity:
                return Response(
                    {'error': f'Insufficient stock. Available: {product.current_stock}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            product.current_stock -= quantity
            if not notes:
                notes = f'Stock removal - {quantity} units removed'
        else:
            old_stock = product.current_stock
            product.current_stock = quantity
            if not notes:
                notes = f'Stock adjustment - changed from {old_stock} to {quantity}'
        
        product.save()
        
        StockEntry.objects.create(
            product=product,
            entry_type=entry_type,
            quantity=quantity,
            supplier=supplier,
            notes=notes,
            recorded_by=request.user
        )
        
        AuditLog.objects.create(
            action='Stock Edit',
            user=request.user,
            description=f'Stock adjusted for {product.code}: {entry_type} - {quantity} units',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({
            'id': product.id,
            'code': product.code,
            'current_stock': product.current_stock,
            'adjustment': quantity,
            'type': entry_type,
            'message': f'Stock adjusted successfully'
        })


# ========================
# Stock Entry ViewSet
# ========================
class StockEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockEntry.objects.select_related('product', 'supplier', 'recorded_by').order_by('-created_at')
    serializer_class = StockEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['product', 'entry_type', 'supplier']
    search_fields = ['product__code', 'product__name']
    ordering_fields = ['created_at']


# ========================
# Monthly Opening Stock ViewSet
# ========================
class MonthlyOpeningStockViewSet(viewsets.ModelViewSet):
    queryset = MonthlyOpeningStock.objects.select_related('product', 'recorded_by')
    serializer_class = MonthlyOpeningStockSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['product', 'month']
    ordering_fields = ['month']
    ordering = ['-month']


# ========================
# Audit Log ViewSet
# ========================
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('user').order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['action', 'user']
    search_fields = ['description']
    ordering_fields = ['timestamp']


# ========================
# Dashboard ViewSet
# ========================
class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get dashboard summary with all stats and chart data"""
        from django.db.models import Count
        from django.db.models.functions import TruncMonth
        import calendar
        
        # Basic stats
        total_products = Product.objects.filter(is_active=True).count()
        low_stock_items = Product.objects.filter(current_stock__lte=F('minimum_stock')).count()
        
        total_sales = Sale.objects.count()
        outstanding_invoices = Sale.objects.filter(
            line_items__supply_status__in=['Not Supplied', 'Partially Supplied']
        ).distinct().count()
        outstanding_sales = Sale.objects.filter(outstanding_balance__gt=0).count()
        
        total_revenue = Sale.objects.aggregate(
            total=Sum('total_amount', output_field=DecimalField())
        )['total'] or 0
        
        total_outstanding = Sale.objects.aggregate(
            total=Sum('outstanding_balance', output_field=DecimalField())
        )['total'] or 0
        
        stock_entries_count = StockEntry.objects.count()
        
        # Monthly Sales Data (for line chart)
        current_year = timezone.now().year
        monthly_sales_query = Sale.objects.filter(
            created_at__year=current_year
        ).annotate(
            month_num=TruncMonth('created_at')
        ).values('month_num').annotate(
            total=Sum('total_amount', output_field=DecimalField())
        ).order_by('month_num')
        
        # Create a dictionary with all months initialized to 0
        monthly_sales_dict = {i: 0 for i in range(1, 13)}
        
        # Fill in actual sales data
        for entry in monthly_sales_query:
            month_num = entry['month_num'].month
            monthly_sales_dict[month_num] = float(entry['total'] or 0)
        
        # Format for frontend
        monthly_sales = [
            {
                'month': calendar.month_abbr[month],
                'total': monthly_sales_dict[month]
            }
            for month in range(1, 13)
        ]
        
        # Top Selling Products (for pie chart)
        top_products_query = SaleLineItem.objects.values(
            'product__code'  # Use product code (short name)
        ).annotate(
            total_quantity=Sum('quantity_supplied')
        ).order_by('-total_quantity')[:5]
        
        top_products = [
            {
                'name': item['product__code'],
                'value': item['total_quantity']
            }
            for item in top_products_query
        ]
        
        data = {
            'total_products': total_products,
            'low_stock_items': low_stock_items,
            'total_sales': total_sales,
            'outstanding_invoices': outstanding_invoices,
            'outstanding_sales': outstanding_sales,
            'total_revenue': total_revenue,
            'total_outstanding': total_outstanding,
            'stock_entries_count': stock_entries_count,
            'monthly_sales': monthly_sales,
            'top_products': top_products,
        }
        
        serializer = DashboardSummarySerializer(data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def monthly_sales(self, request):
        """Get monthly sales data for line chart"""
        from django.db.models.functions import TruncMonth
        import calendar
        
        current_year = timezone.now().year
        
        monthly_sales_query = Sale.objects.filter(
            created_at__year=current_year
        ).annotate(
            month_num=TruncMonth('created_at')
        ).values('month_num').annotate(
            total=Sum('total_amount', output_field=DecimalField())
        ).order_by('month_num')
        
        # Create a dictionary with all months initialized to 0
        monthly_sales_dict = {i: 0 for i in range(1, 13)}
        
        # Fill in actual sales data
        for entry in monthly_sales_query:
            month_num = entry['month_num'].month
            monthly_sales_dict[month_num] = float(entry['total'] or 0)
        
        # Format for frontend
        monthly_sales = [
            {
                'month': calendar.month_abbr[month],
                'total': monthly_sales_dict[month]
            }
            for month in range(1, 13)
        ]
        
        return Response(monthly_sales)
    
    @action(detail=False, methods=['get'])
    def top_products(self, request):
        """Get top selling products for pie chart"""
        limit = int(request.query_params.get('limit', 5))
        
        top_products_query = SaleLineItem.objects.values(
            'product__code'  # Use product code (short name)
        ).annotate(
            total_quantity=Sum('quantity_supplied')
        ).order_by('-total_quantity')[:limit]
        
        top_products = [
            {
                'name': item['product__code'],
                'value': item['total_quantity']
            }
            for item in top_products_query
        ]
        
        return Response(top_products)
    
    @action(detail=False, methods=['get'])
    def recent_sales(self, request):
        """Get recent sales"""
        days = request.query_params.get('days', 30)
        since = timezone.now() - timedelta(days=int(days))
        
        sales = Sale.objects.filter(created_at__gte=since).order_by('-created_at')[:20]
        serializer = SaleSerializer(sales, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def top_customers(self, request):
        """Get top customers by total sales"""
        limit = request.query_params.get('limit', 10)
        
        customers = Customer.objects.annotate(
            total_sales=Sum('sales__total_amount')
        ).order_by('-total_sales')[:int(limit)]
        
        data = [
            {
                'id': c.id,
                'company_name': c.company_name,
                'total_sales': c.total_sales or 0
            }
            for c in customers
        ]
        return Response(data)


# ========================
# Sale ViewSet
# ========================
class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.select_related(
        'customer',
        'recorded_by'
    ).prefetch_related(
        'line_items__product__category',
        'line_items__product__subcategory'
    ).order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer', 'mode_of_payment', 'created_at']
    search_fields = [
        'sale_number', 'customer__company_name', 
        'lpo_quotation_number', 'delivery_number',
        'line_items__product__code', 'line_items__product__name'
    ]
    ordering_fields = ['created_at', 'total_amount']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SaleCreateSerializer
        return SaleSerializer
    
    @action(detail=False, methods=['get'])
    def outstanding(self, request):
        """Get all sales with outstanding supplies"""
        sales = self.queryset.filter(
            line_items__supply_status__in=['Not Supplied', 'Partially Supplied']
        ).distinct()
        serializer = self.get_serializer(sales, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search_products(self, request):
        """Search products for autocomplete"""
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response([])
        
        products = Product.objects.filter(
            Q(code__icontains=query) | Q(name__icontains=query),
            is_active=True
        ).select_related('category', 'subcategory')[:10]
        
        data = [{
            'id': p.id,
            'code': p.code,
            'name': p.name,
            'unit_price': str(p.unit_price),
            'current_stock': p.current_stock,
            'category': p.category.name if p.category else '',
            'subcategory': p.subcategory.name if p.subcategory else ''
        } for p in products]
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def search_customers(self, request):
        """Search customers for autocomplete"""
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response([])
        
        customers = Customer.objects.filter(
            Q(company_name__icontains=query) | Q(phone__icontains=query),
            is_active=True
        )[:10]
        
        data = [{
            'id': c.id,
            'company_name': c.company_name,
            'phone': c.phone
        } for c in customers]
        
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def update_line_item_supply(self, request, pk=None):
        """Update supply status for a specific line item"""
        sale = self.get_object()
        line_item_id = request.data.get('line_item_id')
        new_quantity = request.data.get('quantity_supplied', 0)
        new_status = request.data.get('supply_status')
        
        if not line_item_id or not new_status:
            return Response(
                {'error': 'line_item_id and supply_status are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            line_item = sale.line_items.get(id=line_item_id)
        except SaleLineItem.DoesNotExist:
            return Response(
                {'error': 'Line item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        old_supplied = line_item.quantity_supplied
        diff = new_quantity - old_supplied
        
        if diff != 0 and new_status in ['Supplied', 'Partially Supplied']:
            product = line_item.product
            if product.current_stock < diff:
                return Response(
                    {'error': f'Insufficient stock for {product.name}. Available: {product.current_stock}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            product.current_stock -= diff
            product.save()
            
            StockEntry.objects.create(
                product=product,
                entry_type='Out',
                quantity=diff,
                notes=f'Supply update for sale {sale.sale_number} - {product.code}',
                recorded_by=request.user
            )
        
        line_item.quantity_supplied = new_quantity
        line_item.supply_status = new_status
        line_item.save()
        
        AuditLog.objects.create(
            action='Supply Update',
            user=request.user,
            description=f'Supply updated for sale {sale.sale_number}, item {line_item.product.code}: {new_status} ({new_quantity})',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        sale.refresh_from_db()
        serializer = self.get_serializer(sale)
        return Response(serializer.data)