# views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, DecimalField, F
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from decimal import Decimal, ROUND_HALF_UP

from .models import (
    UserProfile, Category, SubCategory, SubSubCategory, ProductGroup, Supplier, Customer, Product,
    Salesperson, MonthlyOpeningStock, StockEntry, StockMovement, AuditLog, Sale, SaleLineItem, DeliveryRecord, DeliveryLineItem,
)
from .serializers import (
    UserSerializer, UserDetailSerializer,
    CategorySerializer, SubCategorySerializer, SubSubCategorySerializer, ProductGroupSerializer,
    SupplierSerializer, CustomerSerializer,
    ProductSerializer, ProductDetailSerializer, SalespersonSerializer,
    StockEntrySerializer, StockMovementSerializer, MonthlyOpeningStockSerializer,
    AuditLogSerializer, DashboardSummarySerializer, SaleSerializer, SaleCreateSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer, SaleApprovalSerializer,
    DeliveryRecordSerializer, DeliveryRecordCreateSerializer
)

# ========================
# Custom JWT Login View
# ========================
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        try:
            role = user.profile.role
        except UserProfile.DoesNotExist:
            role = 'staff'

        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': role,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        }

        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


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
# Salesperson ViewSet
# ========================
class SalespersonViewSet(viewsets.ModelViewSet):
    queryset = Salesperson.objects.all()
    serializer_class = SalespersonSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        salesperson = self.get_object()
        salesperson.is_active = not salesperson.is_active
        salesperson.save()
        return Response({'is_active': salesperson.is_active})


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

        direction = None
        reason = None

        if entry_type == 'In':
            direction = 'IN'
            reason = 'RESTOCK' if supplier else 'ADJUSTMENT'
            product.current_stock += quantity
            if not notes:
                notes = f'Stock replenishment - {quantity} units added'
                if supplier:
                    notes += f' from {supplier.company_name}'

        elif entry_type == 'Out':
            direction = 'OUT'
            reason = 'DAMAGE'
            if product.current_stock < quantity:
                return Response(
                    {'error': f'Insufficient stock. Available: {product.current_stock}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            product.current_stock -= quantity
            if not notes:
                notes = f'Stock removal - {quantity} units removed'

        else:  # Adjustment
            direction = 'IN'
            reason = 'ADJUSTMENT'
            old_stock = product.current_stock
            product.current_stock = quantity
            if not notes:
                notes = f'Stock adjustment - changed from {old_stock} to {quantity}'

        product.save()

        StockMovement.objects.create(
            product=product,
            direction=direction,
            reason=reason,
            quantity=quantity if entry_type != 'Adjustment' else abs(quantity - product.current_stock),
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
            'message': 'Stock adjusted successfully'
        })


# ========================
# Stock Movement ViewSet
# ========================
class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related(
        'product__category',
        'product__subcategory',
        'product__subsubcategory',
        'supplier',
        'sale',
        'recorded_by'
    ).order_by('-created_at')
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['product', 'direction', 'reason', 'supplier']
    search_fields = ['product__code', 'product__name', 'notes']
    ordering_fields = ['created_at']

    @action(detail=False, methods=['get'])
    def stock_in(self, request):
        movements = self.queryset.filter(direction='IN')
        page = self.paginate_queryset(movements)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(movements, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stock_out(self, request):
        movements = self.queryset.filter(direction='OUT')
        page = self.paginate_queryset(movements)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(movements, many=True)
        return Response(serializer.data)


# ========================
# Legacy Stock Entry ViewSet (Read-Only)
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
        from django.db.models import Count
        from django.db.models.functions import TruncMonth
        import calendar

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

        stock_movements_count = StockMovement.objects.count()

        current_year = timezone.now().year
        monthly_sales_query = Sale.objects.filter(
            created_at__year=current_year
        ).annotate(
            month_num=TruncMonth('created_at')
        ).values('month_num').annotate(
            total=Sum('total_amount', output_field=DecimalField())
        ).order_by('month_num')

        monthly_sales_dict = {i: 0 for i in range(1, 13)}
        for entry in monthly_sales_query:
            month_num = entry['month_num'].month
            monthly_sales_dict[month_num] = float(entry['total'] or 0)

        monthly_sales = [
            {'month': calendar.month_abbr[month], 'total': monthly_sales_dict[month]}
            for month in range(1, 13)
        ]

        top_products_query = SaleLineItem.objects.values(
            'product__code'
        ).annotate(
            total_quantity=Sum('quantity_supplied')
        ).order_by('-total_quantity')[:5]

        top_products = [
            {'name': item['product__code'], 'value': item['total_quantity']}
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
            'stock_entries_count': stock_movements_count,
            'monthly_sales': monthly_sales,
            'top_products': top_products,
        }

        serializer = DashboardSummarySerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def monthly_sales(self, request):
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

        monthly_sales_dict = {i: 0 for i in range(1, 13)}
        for entry in monthly_sales_query:
            month_num = entry['month_num'].month
            monthly_sales_dict[month_num] = float(entry['total'] or 0)

        monthly_sales = [
            {'month': calendar.month_abbr[month], 'total': monthly_sales_dict[month]}
            for month in range(1, 13)
        ]

        return Response(monthly_sales)

    @action(detail=False, methods=['get'])
    def top_products(self, request):
        limit = int(request.query_params.get('limit', 5))
        top_products_query = SaleLineItem.objects.values(
            'product__code'
        ).annotate(
            total_quantity=Sum('quantity_supplied')
        ).order_by('-total_quantity')[:limit]

        top_products = [
            {'name': item['product__code'], 'value': item['total_quantity']}
            for item in top_products_query
        ]
        return Response(top_products)

    @action(detail=False, methods=['get'])
    def recent_sales(self, request):
        days = request.query_params.get('days', 30)
        since = timezone.now() - timedelta(days=int(days))
        sales = Sale.objects.filter(created_at__gte=since).order_by('-created_at')[:20]
        serializer = SaleSerializer(sales, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def top_customers(self, request):
        limit = request.query_params.get('limit', 10)
        customers = Customer.objects.annotate(
            total_sales=Sum('sales__total_amount')
        ).order_by('-total_sales')[:int(limit)]

        data = [
            {'id': c.id, 'company_name': c.company_name, 'total_sales': c.total_sales or 0}
            for c in customers
        ]
        return Response(data)


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.select_related(
        'customer', 'recorded_by', 'approved_by'
    ).prefetch_related(
        'line_items__product__category',
        'line_items__product__subcategory'
    ).order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer', 'mode_of_payment', 'status', 'created_at']
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
    def pending(self, request):
        try:
            role = request.user.profile.role
        except UserProfile.DoesNotExist:
            role = 'staff'

        if role != 'admin':
            return Response(
                {'error': 'Only admins can view pending approvals.'},
                status=status.HTTP_403_FORBIDDEN
            )

        pending_sales = self.queryset.filter(status='pending')
        serializer = self.get_serializer(pending_sales, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        try:
            role = request.user.profile.role
        except UserProfile.DoesNotExist:
            role = 'staff'

        if role != 'admin':
            return Response(
                {'error': 'Only admins can approve or reject sales.'},
                status=status.HTTP_403_FORBIDDEN
            )

        sale = self.get_object()

        if sale.status != 'pending':
            return Response(
                {'error': f'Sale is already {sale.status}. Only pending sales can be actioned.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SaleApprovalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        action_type = serializer.validated_data['action']

        if action_type == 'approve':
            # ── Stock check ───────────────────────────────────────────────────
            stock_errors = []
            for item in sale.line_items.all():
                if item.supply_status in ['Supplied', 'Partially Supplied']:
                    if item.product.current_stock < item.quantity_supplied:
                        stock_errors.append(
                            f"{item.product.name}: Available {item.product.current_stock}, "
                            f"Required {item.quantity_supplied}"
                        )

            if stock_errors:
                return Response(
                    {'error': 'Insufficient stock for some items.', 'details': stock_errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # ─────────────────────────────────────────────────────────────────

            # ── VAT recalculation at approval time ────────────────────────────
            apply_vat = serializer.validated_data.get('apply_vat', False)
            sale.vat_applied = apply_vat

            if apply_vat:
                sale.vat_amount = (sale.subtotal * Decimal('0.16')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                sale.total_amount = (sale.subtotal + sale.vat_amount).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            else:
                sale.vat_amount = Decimal('0.00')
                sale.total_amount = sale.subtotal.quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )

            sale.outstanding_balance = (sale.total_amount - sale.amount_paid).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            if sale.outstanding_balance < Decimal('0.00'):
                sale.outstanding_balance = Decimal('0.00')
            # ─────────────────────────────────────────────────────────────────

            sale.deduct_stock(approved_by_user=request.user)
            sale.status = 'approved'
            sale.approved_by = request.user
            sale.approved_at = timezone.now()
            sale.save()

            AuditLog.objects.create(
                action='Sale Approved',
                user=request.user,
                description=(
                    f'Sale {sale.sale_number} approved by {request.user.username}'
                    f'{" with VAT" if apply_vat else " (VAT exempt)"}'
                ),
                ip_address=request.META.get('REMOTE_ADDR')
            )

            sale.refresh_from_db()
            return Response({
                'message': f'Sale {sale.sale_number} approved successfully. Stock has been deducted.',
                'sale': SaleSerializer(sale).data
            })

        elif action_type == 'reject':
            sale.status = 'rejected'
            sale.rejection_reason = serializer.validated_data.get('rejection_reason', '')
            sale.save()

            AuditLog.objects.create(
                action='Sale Rejected',
                user=request.user,
                description=(
                    f'Sale {sale.sale_number} rejected by {request.user.username}. '
                    f'Reason: {sale.rejection_reason}'
                ),
                ip_address=request.META.get('REMOTE_ADDR')
            )

            sale.refresh_from_db()
            return Response({
                'message': f'Sale {sale.sale_number} has been rejected.',
                'sale': SaleSerializer(sale).data
            })

    @action(detail=False, methods=['get'])
    def outstanding(self, request):
        sales = self.queryset.filter(
            status='approved',
            line_items__supply_status__in=['Not Supplied', 'Partially Supplied']
        ).distinct()
        serializer = self.get_serializer(sales, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def record_delivery(self, request, pk=None):
        sale = self.get_object()

        if sale.status != 'approved':
            return Response(
                {'error': 'Deliveries can only be recorded for approved sales.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DeliveryRecordCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        delivery_date = serializer.validated_data['delivery_date']
        notes = serializer.validated_data.get('notes', '')
        items_data = serializer.validated_data['items']

        errors = []
        for item_data in items_data:
            try:
                line_item = sale.line_items.get(id=item_data['line_item_id'])
            except SaleLineItem.DoesNotExist:
                errors.append(f"Line item {item_data['line_item_id']} not found.")
                continue

            outstanding = line_item.quantity_ordered - line_item.quantity_supplied
            if item_data['quantity_delivered'] != outstanding:
                errors.append(
                    f"{line_item.product.name}: must deliver exactly "
                    f"{outstanding} (the full outstanding quantity)."
                )

            if line_item.product.current_stock < item_data['quantity_delivered']:
                errors.append(
                    f"{line_item.product.name}: insufficient stock. "
                    f"Available: {line_item.product.current_stock}, "
                    f"Required: {item_data['quantity_delivered']}."
                )

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        delivery = DeliveryRecord.objects.create(
            sale=sale,
            delivery_date=delivery_date,
            notes=notes,
            recorded_by=request.user
        )

        for item_data in items_data:
            line_item = sale.line_items.get(id=item_data['line_item_id'])
            qty = item_data['quantity_delivered']

            DeliveryLineItem.objects.create(
                delivery=delivery,
                line_item=line_item,
                quantity_delivered=qty
            )

            line_item.quantity_supplied += qty
            line_item.supply_status = 'Supplied'
            line_item.save()

            line_item.product.current_stock -= qty
            line_item.product.save()

            StockMovement.objects.create(
                product=line_item.product,
                direction='OUT',
                reason='SALE',
                quantity=qty,
                sale=sale,
                notes=f"Delivery on {delivery_date} for sale {sale.sale_number}",
                recorded_by=request.user
            )

        AuditLog.objects.create(
            action='Supply Update',
            user=request.user,
            description=(
                f'Delivery recorded for sale {sale.sale_number} '
                f'on {delivery_date} by {request.user.username}'
            ),
            ip_address=request.META.get('REMOTE_ADDR')
        )

        sale.refresh_from_db()
        return Response({
            'message': f'Delivery recorded successfully for sale {sale.sale_number}.',
            'sale': SaleSerializer(sale).data
        })

    @action(detail=True, methods=['get'])
    def delivery_history(self, request, pk=None):
        sale = self.get_object()
        deliveries = sale.delivery_records.prefetch_related(
            'delivery_items__line_item__product'
        ).all()
        serializer = DeliveryRecordSerializer(deliveries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search_products(self, request):
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
        sale = self.get_object()

        if sale.status != 'approved':
            return Response(
                {'error': 'Supply can only be updated on approved sales.'},
                status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response({'error': 'Line item not found'}, status=status.HTTP_404_NOT_FOUND)

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

            StockMovement.objects.create(
                product=product,
                direction='OUT',
                reason='SALE',
                quantity=diff,
                sale=sale,
                notes=f'Supply update for sale {sale.sale_number} - {product.code}',
                recorded_by=request.user
            )

        line_item.quantity_supplied = new_quantity
        line_item.supply_status = new_status
        line_item.save()

        AuditLog.objects.create(
            action='Supply Update',
            user=request.user,
            description=(
                f'Supply updated for sale {sale.sale_number}, '
                f'item {line_item.product.code}: {new_status} ({new_quantity})'
            ),
            ip_address=request.META.get('REMOTE_ADDR')
        )

        sale.refresh_from_db()
        serializer = self.get_serializer(sale)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search_salespersons(self, request):
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response([])

        salespersons = Salesperson.objects.filter(
            Q(name__icontains=query),
            is_active=True
        )[:10]

        data = [{
            'id': s.id,
            'name': s.name,
            'phone': s.phone,
        } for s in salespersons]

        return Response(data)

# ========================
# Password Reset Views
# ========================
@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    serializer = PasswordResetRequestSerializer(data=request.data)
    if serializer.is_valid():
        try:
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': 'Failed to send reset email. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if serializer.is_valid():
        try:
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': 'Failed to reset password. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def password_reset_validate(request, uid, token):
    from django.contrib.auth.tokens import PasswordResetTokenGenerator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str

    try:
        uid_decoded = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=uid_decoded)
        token_generator = PasswordResetTokenGenerator()

        if token_generator.check_token(user, token):
            return Response({'valid': True}, status=status.HTTP_200_OK)
        else:
            return Response(
                {'valid': False, 'error': 'Invalid or expired link'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response(
            {'valid': False, 'error': 'Invalid reset link'},
            status=status.HTTP_400_BAD_REQUEST
        )