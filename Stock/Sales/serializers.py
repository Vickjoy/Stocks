# serializers.py
from rest_framework import serializers
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth.models import User
from .models import (
    Category, SubCategory, SubSubCategory, ProductGroup, Supplier, Customer, Product,
    MonthlyOpeningStock, StockEntry, AuditLog, Sale, SaleLineItem
)


# ========================
# User Serializers
# ========================
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser']
        read_only_fields = ['id']


class UserDetailSerializer(serializers.ModelSerializer):
    groups = serializers.StringRelatedField(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'groups', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']


# ========================
# SubSubCategory Serializers
# ========================
class SubSubCategorySerializer(serializers.ModelSerializer):
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    category_name = serializers.CharField(source='subcategory.category.name', read_only=True)
    
    class Meta:
        model = SubSubCategory
        fields = ['id', 'name', 'description', 'subcategory', 'subcategory_name', 'category_name', 'created_at']
        read_only_fields = ['id', 'created_at']


# ========================
# SubCategory Serializers
# ========================
class SubCategorySerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_name = serializers.CharField(source='category.name', read_only=True)
    subsubcategories = SubSubCategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = SubCategory
        fields = ['id', 'category', 'category_name', 'name', 'description', 'subsubcategories', 'created_at']
        read_only_fields = ['id', 'created_at']


# ========================
# Category Serializers
# ========================
class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'subcategories', 'created_at']
        read_only_fields = ['id', 'created_at']


# ========================
# ProductGroup Serializers (Deprecated)
# ========================
class ProductGroupSerializer(serializers.ModelSerializer):
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    category_name = serializers.CharField(source='subcategory.category.name', read_only=True)
    
    class Meta:
        model = ProductGroup
        fields = ['id', 'name', 'description', 'subcategory', 'subcategory_name', 
                  'category_name', 'created_at']
        read_only_fields = ['id', 'created_at']


# ========================
# Supplier Serializer
# ========================
class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'company_name', 'phone', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# ========================
# Customer Serializer
# ========================
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'company_name', 'phone', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# ========================
# Product Serializers
# ========================
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    subsubcategory_name = serializers.CharField(source='subsubcategory.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'code', 'name', 'description',
            'category', 'category_name',
            'subcategory', 'subcategory_name',
            'subsubcategory', 'subsubcategory_name',
            'unit_price', 'current_stock', 'minimum_stock',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Ensure category hierarchy is valid"""
        category = data.get('category')
        subcategory = data.get('subcategory')
        subsubcategory = data.get('subsubcategory')
        
        if category and subcategory:
            if subcategory.category != category:
                raise serializers.ValidationError({
                    'subcategory': 'Subcategory does not belong to the selected category.'
                })
        
        if subcategory and subsubcategory:
            if subsubcategory.subcategory != subcategory:
                raise serializers.ValidationError({
                    'subsubcategory': 'Sub-subcategory does not belong to the selected subcategory.'
                })
        
        return data


class ProductDetailSerializer(ProductSerializer):
    stock_entries = serializers.SerializerMethodField()
    
    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields + ['stock_entries']
    
    def get_stock_entries(self, obj):
        entries = obj.stock_entries.all().order_by('-created_at')[:10]
        return StockEntrySerializer(entries, many=True).data


# ========================
# Stock Entry Serializers
# ========================
class StockEntrySerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    subcategory_name = serializers.CharField(source='product.subcategory.name', read_only=True)
    subsubcategory_name = serializers.CharField(source='product.subsubcategory.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    
    class Meta:
        model = StockEntry
        fields = [
            'id', 'product', 'product_code', 'product_name',
            'category_name', 'subcategory_name', 'subsubcategory_name',
            'entry_type', 'quantity',
            'supplier', 'supplier_name',
            'notes', 'recorded_by', 'recorded_by_name',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# ========================
# Monthly Opening Stock Serializer
# ========================
class MonthlyOpeningStockSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    
    class Meta:
        model = MonthlyOpeningStock
        fields = ['id', 'product', 'product_code', 'product_name', 'month', 'opening_quantity', 
                  'recorded_by', 'recorded_by_name', 'recorded_at']
        read_only_fields = ['id', 'recorded_at']


# ========================
# Audit Log Serializer
# ========================
class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'user', 'user_name', 'description', 'ip_address', 'timestamp']
        read_only_fields = ['id', 'timestamp']


# ========================
# Dashboard Summary Serializer
# ========================
class DashboardSummarySerializer(serializers.Serializer):
    total_products = serializers.IntegerField()
    low_stock_items = serializers.IntegerField()
    total_sales = serializers.IntegerField()
    outstanding_sales = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_outstanding = serializers.DecimalField(max_digits=12, decimal_places=2)


# ========================
# Sale Serializers
# ========================
class SaleLineItemSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    outstanding_quantity = serializers.SerializerMethodField()

    class Meta:
        model = SaleLineItem
        fields = [
            'id', 'product', 'product_code', 'product_name',
            'quantity_ordered', 'quantity_supplied', 'outstanding_quantity',
            'supply_status', 'unit_price', 'subtotal'
        ]
        read_only_fields = ['id', 'subtotal']

    def get_outstanding_quantity(self, obj):
        return obj.outstanding_quantity()

    def validate(self, data):
        quantity_ordered = data.get('quantity_ordered', 0)
        quantity_supplied = data.get('quantity_supplied', 0)
        supply_status = data.get('supply_status')

        if supply_status == 'Supplied':
            data['quantity_supplied'] = quantity_ordered
        elif supply_status == 'Not Supplied':
            data['quantity_supplied'] = 0
        elif supply_status == 'Partially Supplied':
            if quantity_supplied <= 0 or quantity_supplied >= quantity_ordered:
                raise serializers.ValidationError(
                    "For partially supplied, quantity must be between 0 and ordered quantity"
                )

        product = data.get('product')
        if supply_status in ['Supplied', 'Partially Supplied']:
            if product.current_stock < data['quantity_supplied']:
                raise serializers.ValidationError(
                    f"Insufficient stock for {product.name}. Available: {product.current_stock}, Required: {data['quantity_supplied']}"
                )

        return data


class SaleSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.company_name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    line_items = SaleLineItemSerializer(many=True, read_only=True)
    has_outstanding = serializers.SerializerMethodField()
    is_fully_paid = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            'id', 'sale_number', 'customer', 'customer_name',
            'lpo_quotation_number', 'delivery_number',
            'mode_of_payment', 'amount_paid', 'total_amount', 'outstanding_balance',
            'line_items', 'has_outstanding', 'is_fully_paid',
            'recorded_by', 'recorded_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sale_number', 'total_amount', 'outstanding_balance', 'created_at', 'updated_at']

    def get_has_outstanding(self, obj):
        return obj.has_outstanding_supplies()
    
    def get_is_fully_paid(self, obj):
        return obj.is_fully_paid()


class SaleCreateSerializer(serializers.ModelSerializer):
    line_items = SaleLineItemSerializer(many=True)

    class Meta:
        model = Sale
        fields = [
            'customer', 'lpo_quotation_number', 'delivery_number',
            'mode_of_payment', 'amount_paid', 'line_items'
        ]

    def validate(self, data):
        mode_of_payment = data.get('mode_of_payment')
        amount_paid = data.get('amount_paid', 0)

        if mode_of_payment == 'Not Paid':
            data['amount_paid'] = Decimal('0.00')
        elif mode_of_payment in ['Cash', 'Cheque', 'Mpesa']:
            if not amount_paid or amount_paid <= 0:
                raise serializers.ValidationError({
                    'amount_paid': 'Amount paid is required when payment mode is selected'
                })
            data['amount_paid'] = Decimal(str(amount_paid)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        line_items = data.get('line_items', [])
        if not line_items:
            raise serializers.ValidationError({
                'line_items': 'At least one product must be added to the sale'
            })

        return data

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items')
        validated_data['recorded_by'] = self.context['request'].user

        sale = Sale.objects.create(**validated_data)

        for item_data in line_items_data:
            SaleLineItem.objects.create(sale=sale, **item_data)

        sale.calculate_total()

        return sale