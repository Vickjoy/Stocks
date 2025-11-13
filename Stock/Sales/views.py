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
    Category, SubCategory, ProductGroup, Supplier, Customer, Product,
    MonthlyOpeningStock, StockEntry, Invoice, InvoiceItem,
    Payment, LPO, AuditLog, Sale
)
from .serializers import (
    UserSerializer, UserDetailSerializer,
    CategorySerializer, SubCategorySerializer, ProductGroupSerializer,
    SupplierSerializer, CustomerSerializer,
    ProductSerializer, ProductDetailSerializer,
    StockEntrySerializer, MonthlyOpeningStockSerializer,
    InvoiceSerializer, InvoiceItemSerializer, InvoiceCreateSerializer,
    PaymentSerializer, LPOSerializer, AuditLogSerializer,
    DashboardSummarySerializer, SaleSerializer, SaleCreateSerializer
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
    queryset = Category.objects.prefetch_related('subcategories__groups')
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ['name']


# ========================
# SubCategory ViewSet
# ========================
class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.select_related('category').prefetch_related('groups')
    serializer_class = SubCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['category']
    search_fields = ['name']


# ========================
# ProductGroup ViewSet (NEW)
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
    search_fields = ['company_name', 'email', 'phone']
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
    filterset_fields = ['payment_type', 'is_active']
    search_fields = ['company_name', 'email', 'phone']
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
    queryset = Product.objects.select_related('subcategory__category', 'group')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subcategory', 'group', 'is_active']
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
# Invoice ViewSet
# ========================
class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related('customer', 'created_by').prefetch_related('items', 'payments').order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'customer', 'created_at']
    search_fields = ['invoice_number', 'customer__company_name']
    ordering_fields = ['created_at', 'total_amount', 'status']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InvoiceCreateSerializer
        return InvoiceSerializer
    
    @action(detail=False, methods=['get'])
    def outstanding(self, request):
        invoices = self.queryset.filter(status__in=['Outstanding', 'Partial'])
        serializer = self.get_serializer(invoices, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def record_payment(self, request, pk=None):
        invoice = self.get_object()
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method')
        reference_number = request.data.get('reference_number', '')
        
        Payment.objects.create(
            invoice=invoice,
            amount=amount,
            payment_method=payment_method,
            reference_number=reference_number,
            recorded_by=request.user
        )
        
        invoice.paid_amount += amount
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = 'Paid'
        else:
            invoice.status = 'Partial'
        invoice.save()
        
        return Response({'status': invoice.status, 'paid_amount': invoice.paid_amount})


# ========================
# Invoice Item ViewSet
# ========================
class InvoiceItemViewSet(viewsets.ModelViewSet):
    queryset = InvoiceItem.objects.select_related('invoice', 'product')
    serializer_class = InvoiceItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['invoice', 'product']


# ========================
# Payment ViewSet
# ========================
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related('invoice', 'recorded_by').order_by('-created_at')
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['invoice', 'payment_method', 'payment_date']
    search_fields = ['invoice__invoice_number', 'reference_number']
    ordering_fields = ['payment_date', 'amount']


# ========================
# LPO ViewSet
# ========================
class LPOViewSet(viewsets.ModelViewSet):
    queryset = LPO.objects.select_related('supplier', 'product', 'created_by').order_by('-created_at')
    serializer_class = LPOSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'supplier', 'product']
    search_fields = ['lpo_number', 'supplier__company_name', 'product__code']
    ordering_fields = ['order_date', 'status']
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        lpos = self.queryset.filter(status__in=['Pending', 'Partial'])
        serializer = self.get_serializer(lpos, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_delivery(self, request, pk=None):
        lpo = self.get_object()
        delivered_qty = request.data.get('delivered_quantity')
        
        lpo.delivered_quantity += delivered_qty
        
        if lpo.delivered_quantity >= lpo.ordered_quantity:
            lpo.status = 'Completed'
            lpo.actual_delivery = timezone.now().date()
        else:
            lpo.status = 'Partial'
        
        lpo.save()
        
        product = lpo.product
        product.current_stock += delivered_qty
        product.save()
        
        return Response({'status': lpo.status, 'delivered_quantity': lpo.delivered_quantity})


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
        total_products = Product.objects.filter(is_active=True).count()
        low_stock_items = Product.objects.filter(current_stock__lte=F('minimum_stock')).count()
        
        outstanding_invoices = Invoice.objects.filter(status__in=['Outstanding', 'Partial']).count()
        pending_lpos = LPO.objects.filter(status__in=['Pending', 'Partial']).count()
        
        total_revenue = Invoice.objects.filter(status='Paid').aggregate(
            total=Sum('total_amount', output_field=DecimalField())
        )['total'] or 0
        
        total_outstanding = Invoice.objects.filter(
            status__in=['Outstanding', 'Partial']
        ).aggregate(
            total=Sum(F('total_amount') - F('paid_amount'), output_field=DecimalField())
        )['total'] or 0
        
        data = {
            'total_products': total_products,
            'low_stock_items': low_stock_items,
            'outstanding_invoices': outstanding_invoices,
            'pending_lpos': pending_lpos,
            'total_revenue': total_revenue,
            'total_outstanding': total_outstanding,
        }
        
        serializer = DashboardSummarySerializer(data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent_sales(self, request):
        days = request.query_params.get('days', 30)
        since = timezone.now() - timedelta(days=int(days))
        
        invoices = Invoice.objects.filter(created_at__gte=since).order_by('-created_at')[:20]
        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def top_customers(self, request):
        limit = request.query_params.get('limit', 10)
        
        customers = Customer.objects.annotate(
            total_sales=Sum('invoices__total_amount')
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
        'product__subcategory__category',
        'customer',
        'recorded_by'
    ).order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['supply_status', 'customer', 'product', 'created_at']
    search_fields = [
        'sale_number', 'product__code', 'product__name',
        'customer__company_name', 'lpo_quotation_number', 'delivery_number'
    ]
    ordering_fields = ['created_at', 'total_amount', 'supply_status']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SaleCreateSerializer
        return SaleSerializer
    
    @action(detail=False, methods=['get'])
    def outstanding(self, request):
        sales = self.queryset.filter(
            supply_status__in=['Not Supplied', 'Partially Supplied']
        ).exclude(
            quantity_supplied=F('quantity_ordered')
        )
        serializer = self.get_serializer(sales, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_customer(self, request):
        customer_id = request.query_params.get('customer_id')
        if not customer_id:
            return Response(
                {'error': 'customer_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sales = self.queryset.filter(
            customer_id=customer_id,
            supply_status__in=['Not Supplied', 'Partially Supplied']
        )
        serializer = self.get_serializer(sales, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_supply(self, request, pk=None):
        sale = self.get_object()
        new_quantity = request.data.get('quantity_supplied', 0)
        new_status = request.data.get('supply_status')
        
        if not new_status:
            return Response(
                {'error': 'supply_status is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_supplied = sale.quantity_supplied
        diff = new_quantity - old_supplied
        
        if diff != 0 and new_status in ['Supplied', 'Partially Supplied']:
            product = sale.product
            if product.current_stock < diff:
                return Response(
                    {'error': 'Insufficient stock for supply update'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            product.current_stock -= diff
            product.save()
            
            StockEntry.objects.create(
                product=product,
                entry_type='Out',
                quantity=diff,
                notes=f'Supply update for sale {sale.sale_number}',
                recorded_by=request.user
            )
        
        sale.quantity_supplied = new_quantity
        sale.supply_status = new_status
        sale.save()
        
        AuditLog.objects.create(
            action='Supply Update',
            user=request.user,
            description=f'Supply updated for sale {sale.sale_number}: {new_status} ({new_quantity})',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({
            'sale_number': sale.sale_number,
            'supply_status': sale.supply_status,
            'quantity_supplied': sale.quantity_supplied
        })