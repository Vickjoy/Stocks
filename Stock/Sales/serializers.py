# serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Category, SubCategory, Supplier, Customer, Product,
    MonthlyOpeningStock, StockEntry, Invoice, InvoiceItem,
    Payment, LPO, AuditLog
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
# Category & SubCategory Serializers
# ========================
class SubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = SubCategory
        fields = ['id', 'category', 'category_name', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'subcategories', 'created_at']
        read_only_fields = ['id', 'created_at']


# ========================
# Supplier Serializer
# ========================
class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'company_name', 'email', 'phone', 'address', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# ========================
# Customer Serializer
# ========================
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'company_name', 'email', 'phone', 'address', 'payment_type', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# ========================
# Product Serializers
# ========================
class ProductSerializer(serializers.ModelSerializer):
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    category_name = serializers.CharField(source='subcategory.category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'code', 'name', 'description', 'subcategory', 'subcategory_name', 'category_name', 
                  'unit_price', 'current_stock', 'minimum_stock', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


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
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    
    class Meta:
        model = StockEntry
        fields = ['id', 'product', 'product_code', 'product_name', 'entry_type', 'quantity', 
                  'supplier', 'supplier_name', 'notes', 'recorded_by', 'recorded_by_name', 'created_at']
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
# Invoice Item Serializers
# ========================
class InvoiceItemSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = InvoiceItem
        fields = ['id', 'product', 'product_code', 'product_name', 'quantity', 'unit_price', 'subtotal']
        read_only_fields = ['id']
    
    def validate(self, data):
        # Ensure quantity and unit_price are positive
        if data.get('quantity', 0) <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        if data.get('unit_price', 0) <= 0:
            raise serializers.ValidationError("Unit price must be greater than 0")
        return data


# ========================
# Payment Serializers
# ========================
class PaymentSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = ['id', 'invoice', 'amount', 'payment_method', 'reference_number', 'payment_date', 
                  'notes', 'recorded_by', 'recorded_by_name', 'created_at']
        read_only_fields = ['id', 'created_at']


# ========================
# Invoice Serializers
# ========================
class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.company_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    remaining_balance = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'customer', 'customer_name', 'total_amount', 'paid_amount', 
                  'remaining_balance', 'status', 'due_date', 'notes', 'items', 'payments', 
                  'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'items', 'payments']
    
    def get_remaining_balance(self, obj):
        return obj.remaining_balance()


class InvoiceCreateSerializer(serializers.ModelSerializer):
    items_data = InvoiceItemSerializer(many=True, write_only=True)
    
    class Meta:
        model = Invoice
        fields = ['customer', 'total_amount', 'paid_amount', 'status', 'due_date', 'notes', 'items_data']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items_data', [])
        invoice = Invoice.objects.create(**validated_data)
        
        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)
        
        return invoice


# ========================
# LPO Serializers
# ========================
class LPOSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    pending_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = LPO
        fields = ['id', 'lpo_number', 'supplier', 'supplier_name', 'product', 'product_code', 'product_name',
                  'ordered_quantity', 'delivered_quantity', 'pending_quantity', 'status', 'order_date', 
                  'expected_delivery', 'actual_delivery', 'notes', 'created_by', 'created_by_name', 
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_pending_quantity(self, obj):
        return obj.pending_quantity()


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
    """Serializer for dashboard summary data"""
    total_products = serializers.IntegerField()
    low_stock_items = serializers.IntegerField()
    outstanding_invoices = serializers.IntegerField()
    pending_lpos = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_outstanding = serializers.DecimalField(max_digits=12, decimal_places=2)