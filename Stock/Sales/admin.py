# admin.py
from django.contrib import admin
from .models import (
    Category, SubCategory, SubSubCategory, ProductGroup, Supplier, Customer, Product,
    MonthlyOpeningStock, StockEntry, Invoice, InvoiceItem,
    Payment, LPO, AuditLog, Sale, SaleLineItem
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']
    list_filter = ['created_at']
    ordering = ['name']


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'description', 'created_at']
    search_fields = ['name', 'category__name']
    list_filter = ['category', 'created_at']
    ordering = ['category', 'name']
    autocomplete_fields = ['category']


@admin.register(SubSubCategory)
class SubSubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'subcategory', 'get_category', 'description', 'created_at']
    search_fields = ['name', 'subcategory__name', 'subcategory__category__name']
    list_filter = ['subcategory__category', 'subcategory', 'created_at']
    ordering = ['subcategory__category', 'subcategory', 'name']
    autocomplete_fields = ['subcategory']
    
    def get_category(self, obj):
        return obj.subcategory.category.name
    get_category.short_description = 'Category'
    get_category.admin_order_field = 'subcategory__category__name'


@admin.register(ProductGroup)
class ProductGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'subcategory', 'get_category', 'description', 'created_at']
    search_fields = ['name', 'subcategory__name']
    list_filter = ['subcategory__category', 'created_at']
    ordering = ['name']
    
    def get_category(self, obj):
        return obj.subcategory.category.name
    get_category.short_description = 'Category'


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'email', 'phone', 'is_active', 'created_at']
    search_fields = ['company_name', 'email', 'phone']
    list_filter = ['is_active', 'created_at']
    ordering = ['company_name']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'email', 'phone', 'payment_type', 'is_active', 'created_at']
    search_fields = ['company_name', 'email', 'phone']
    list_filter = ['payment_type', 'is_active', 'created_at']
    ordering = ['company_name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'category', 'subcategory', 'subsubcategory',
        'unit_price', 'current_stock', 'minimum_stock', 'is_active'
    ]
    search_fields = ['code', 'name', 'description']
    list_filter = [
        'category', 'subcategory', 'subsubcategory',
        'is_active', 'created_at'
    ]
    ordering = ['code']
    autocomplete_fields = ['category', 'subcategory', 'subsubcategory', 'group']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description')
        }),
        ('Category Hierarchy', {
            'fields': ('category', 'subcategory', 'subsubcategory', 'group')
        }),
        ('Stock & Pricing', {
            'fields': ('unit_price', 'current_stock', 'minimum_stock', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MonthlyOpeningStock)
class MonthlyOpeningStockAdmin(admin.ModelAdmin):
    list_display = ['product', 'month', 'opening_quantity', 'recorded_by', 'recorded_at']
    search_fields = ['product__code', 'product__name']
    list_filter = ['month', 'recorded_at']
    ordering = ['-month']
    autocomplete_fields = ['product', 'recorded_by']


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ['product', 'entry_type', 'quantity', 'supplier', 'recorded_by', 'created_at']
    search_fields = ['product__code', 'product__name', 'notes']
    list_filter = ['entry_type', 'created_at']
    ordering = ['-created_at']
    autocomplete_fields = ['product', 'supplier', 'recorded_by']
    readonly_fields = ['created_at']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'customer', 'total_amount', 'paid_amount',
        'status', 'due_date', 'created_at'
    ]
    search_fields = ['invoice_number', 'customer__company_name']
    list_filter = ['status', 'created_at', 'due_date']
    ordering = ['-created_at']
    autocomplete_fields = ['customer', 'created_by']
    readonly_fields = ['created_at', 'updated_at']


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    autocomplete_fields = ['product']


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'product', 'quantity', 'unit_price', 'subtotal']
    search_fields = ['invoice__invoice_number', 'product__code', 'product__name']
    list_filter = ['invoice__created_at']
    autocomplete_fields = ['invoice', 'product']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'invoice', 'amount', 'payment_method', 'reference_number',
        'payment_date', 'recorded_by', 'created_at'
    ]
    search_fields = ['invoice__invoice_number', 'reference_number']
    list_filter = ['payment_method', 'payment_date', 'created_at']
    ordering = ['-created_at']
    autocomplete_fields = ['invoice', 'recorded_by']
    readonly_fields = ['created_at']


@admin.register(LPO)
class LPOAdmin(admin.ModelAdmin):
    list_display = [
        'lpo_number', 'supplier', 'product', 'ordered_quantity',
        'delivered_quantity', 'status', 'order_date'
    ]
    search_fields = ['lpo_number', 'supplier__company_name', 'product__code']
    list_filter = ['status', 'order_date', 'created_at']
    ordering = ['-created_at']
    autocomplete_fields = ['supplier', 'product', 'created_by']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'description', 'ip_address', 'timestamp']
    search_fields = ['action', 'user__username', 'description']
    list_filter = ['action', 'timestamp']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']


class SaleLineItemInline(admin.TabularInline):
    model = SaleLineItem
    extra = 1
    fields = ['product', 'quantity_ordered', 'quantity_supplied', 'supply_status', 'unit_price', 'subtotal']
    readonly_fields = ['subtotal']
    autocomplete_fields = ['product']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'sale_number', 'customer', 'total_amount', 'mode_of_payment',
        'amount_paid', 'created_at'
    ]
    search_fields = [
        'sale_number', 'customer__company_name',
        'lpo_quotation_number', 'delivery_number'
    ]
    list_filter = ['mode_of_payment', 'created_at']
    ordering = ['-created_at']
    autocomplete_fields = ['customer', 'recorded_by']
    readonly_fields = ['sale_number', 'total_amount', 'created_at', 'updated_at']
    inlines = [SaleLineItemInline]
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('sale_number', 'customer')
        }),
        ('Payment Details', {
            'fields': ('mode_of_payment', 'amount_paid', 'total_amount')
        }),
        ('Reference Numbers', {
            'fields': ('lpo_quotation_number', 'delivery_number')
        }),
        ('Record Keeping', {
            'fields': ('recorded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SaleLineItem)
class SaleLineItemAdmin(admin.ModelAdmin):
    list_display = [
        'sale', 'product', 'quantity_ordered', 'quantity_supplied',
        'supply_status', 'unit_price', 'subtotal'
    ]
    search_fields = [
        'sale__sale_number', 'product__code', 'product__name'
    ]
    list_filter = ['supply_status', 'sale__created_at']
    ordering = ['-sale__created_at']
    autocomplete_fields = ['sale', 'product']
    readonly_fields = ['subtotal']