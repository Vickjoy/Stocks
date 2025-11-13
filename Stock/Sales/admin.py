# admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category, SubCategory, ProductGroup, Supplier, Customer, Product,
    MonthlyOpeningStock, StockEntry, Invoice, InvoiceItem,
    Payment, LPO, AuditLog, Sale
)


class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1
    fields = ['name', 'description']


class ProductGroupInline(admin.TabularInline):
    model = ProductGroup
    extra = 1
    fields = ['name', 'description']


class ProductInline(admin.TabularInline):
    model = Product
    extra = 1
    fields = ['code', 'name', 'unit_price', 'current_stock', 'minimum_stock']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    readonly_fields = ['created_at']
    inlines = [SubCategoryInline]


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['name', 'category__name']
    readonly_fields = ['created_at']
    inlines = [ProductGroupInline]


@admin.register(ProductGroup)
class ProductGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'subcategory', 'get_category', 'product_count', 'created_at']
    list_filter = ['subcategory__category', 'subcategory', 'created_at']
    search_fields = ['name', 'subcategory__name']
    readonly_fields = ['created_at']
    inlines = [ProductInline]
    
    def get_category(self, obj):
        return obj.subcategory.category.name
    get_category.short_description = 'Category'
    
    def product_count(self, obj):
        count = obj.products.count()
        return format_html(
            '<span style="color: {};">{} products</span>',
            'green' if count > 0 else 'gray',
            count
        )
    product_count.short_description = 'Products'


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'email', 'phone', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['company_name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('company_name', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'email', 'phone', 'payment_type', 'is_active', 'created_at']
    list_filter = ['payment_type', 'is_active', 'created_at']
    search_fields = ['company_name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('company_name', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address',),
            'classes': ('collapse',)
        }),
        ('Payment Details', {
            'fields': ('payment_type',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'group', 'subcategory', 'unit_price', 'stock_status', 'is_active', 'created_at']
    list_filter = ['group__subcategory__category', 'subcategory', 'group', 'is_active', 'created_at']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Product Details', {
            'fields': ('code', 'name', 'description')
        }),
        ('Organization', {
            'fields': ('subcategory', 'group')
        }),
        ('Pricing & Stock', {
            'fields': ('unit_price', 'current_stock', 'minimum_stock')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def stock_status(self, obj):
        if obj.current_stock <= obj.minimum_stock:
            color = 'red'
            status = 'Low'
        else:
            color = 'green'
            status = 'OK'
        return format_html(
            '<span style="color: {};">{} ({})</span>',
            color,
            status,
            obj.current_stock
        )
    stock_status.short_description = 'Stock Status'


@admin.register(MonthlyOpeningStock)
class MonthlyOpeningStockAdmin(admin.ModelAdmin):
    list_display = ['product', 'month', 'opening_quantity', 'recorded_by', 'recorded_at']
    list_filter = ['month', 'product__subcategory__category']
    search_fields = ['product__code', 'product__name']
    readonly_fields = ['recorded_at']
    
    fieldsets = (
        ('Stock Information', {
            'fields': ('product', 'month', 'opening_quantity')
        }),
        ('Recording Details', {
            'fields': ('recorded_by', 'recorded_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ['product', 'entry_type', 'quantity', 'supplier', 'recorded_by', 'created_at']
    list_filter = ['entry_type', 'created_at', 'product__subcategory__category']
    search_fields = ['product__code', 'product__name', 'supplier__company_name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Stock Movement', {
            'fields': ('product', 'entry_type', 'quantity', 'supplier')
        }),
        ('Details', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Recording', {
            'fields': ('recorded_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ['product', 'quantity', 'unit_price', 'subtotal']
    readonly_fields = ['subtotal']


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1
    fields = ['amount', 'payment_method', 'payment_date', 'reference_number']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'total_amount', 'paid_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'customer']
    search_fields = ['invoice_number', 'customer__company_name']
    readonly_fields = ['created_at', 'updated_at', 'remaining_balance']
    inlines = [InvoiceItemInline, PaymentInline]
    
    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'customer', 'due_date')
        }),
        ('Payment Details', {
            'fields': ('total_amount', 'paid_amount', 'remaining_balance', 'status')
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'product', 'quantity', 'unit_price', 'subtotal']
    list_filter = ['invoice__created_at', 'product__subcategory__category']
    search_fields = ['invoice__invoice_number', 'product__code']
    readonly_fields = ['subtotal']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'payment_method', 'payment_date', 'recorded_by', 'created_at']
    list_filter = ['payment_method', 'payment_date', 'created_at']
    search_fields = ['invoice__invoice_number', 'reference_number']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('invoice', 'amount', 'payment_method', 'payment_date')
        }),
        ('Reference', {
            'fields': ('reference_number', 'notes'),
            'classes': ('collapse',)
        }),
        ('Recording', {
            'fields': ('recorded_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LPO)
class LPOAdmin(admin.ModelAdmin):
    list_display = ['lpo_number', 'supplier', 'product', 'ordered_quantity', 'delivery_progress', 'status', 'order_date']
    list_filter = ['status', 'order_date', 'created_at', 'product__subcategory__category']
    search_fields = ['lpo_number', 'supplier__company_name', 'product__code']
    readonly_fields = ['created_at', 'updated_at', 'pending_quantity']
    
    fieldsets = (
        ('LPO Information', {
            'fields': ('lpo_number', 'supplier', 'product')
        }),
        ('Quantities', {
            'fields': ('ordered_quantity', 'delivered_quantity', 'pending_quantity', 'status')
        }),
        ('Dates', {
            'fields': ('order_date', 'expected_delivery', 'actual_delivery')
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def delivery_progress(self, obj):
        total = obj.ordered_quantity
        delivered = obj.delivered_quantity
        percentage = (delivered / total * 100) if total > 0 else 0
        color = 'green' if delivered == total else 'orange' if delivered > 0 else 'red'
        return format_html(
            '<span style="color: {};">{}/{} ({}%)</span>',
            color,
            delivered,
            total,
            int(percentage)
        )
    delivery_progress.short_description = 'Delivery Progress'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'timestamp', 'ip_address']
    list_filter = ['action', 'timestamp', 'user']
    search_fields = ['user__username', 'description', 'ip_address']
    readonly_fields = ['action', 'user', 'description', 'ip_address', 'timestamp']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'sale_number', 'product', 'customer', 'quantity_ordered',
        'quantity_supplied', 'supply_status_display', 'total_amount',
        'created_at'
    ]
    list_filter = ['supply_status', 'created_at', 'product__subcategory__category']
    search_fields = [
        'sale_number', 'product__code', 'product__name',
        'customer__company_name', 'lpo_quotation_number', 'delivery_number'
    ]
    readonly_fields = ['sale_number', 'total_amount', 'created_at', 'updated_at', 'outstanding_quantity']
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('sale_number', 'product', 'customer')
        }),
        ('Quantity & Supply', {
            'fields': (
                'quantity_ordered', 'quantity_supplied',
                'outstanding_quantity', 'supply_status'
            )
        }),
        ('Pricing', {
            'fields': ('unit_price', 'total_amount')
        }),
        ('References', {
            'fields': ('lpo_quotation_number', 'delivery_number'),
            'classes': ('collapse',)
        }),
        ('Recording Details', {
            'fields': ('recorded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def supply_status_display(self, obj):
        colors = {
            'Supplied': 'green',
            'Partially Supplied': 'orange',
            'Not Supplied': 'red'
        }
        color = colors.get(obj.supply_status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.supply_status
        )
    supply_status_display.short_description = 'Supply Status'