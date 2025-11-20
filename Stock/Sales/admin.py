from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from .models import (
    Category, SubCategory, SubSubCategory,
    Supplier, Customer, Product,
    MonthlyOpeningStock, StockEntry, AuditLog,
    Sale, SaleLineItem
)

# =====================================================
# CUSTOM COMPOSITE WIDGET FOR SUBSUBCATEGORY (FIX)
# =====================================================

class SubSubCategoryCompositeWidget(ForeignKeyWidget):
    """
    Resolves SubSubCategory using BOTH name and subcategory name.
    Prevents MultipleObjectsReturned when names repeat.
    """
    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return None

        subcategory_name = row.get("subcategory")
        if not subcategory_name:
            raise ValueError("❌ Missing 'subcategory' column required for SubSubCategory match.")

        try:
            subcat = SubCategory.objects.get(name=subcategory_name)
        except SubCategory.DoesNotExist:
            raise ValueError(f"❌ SubCategory '{subcategory_name}' not found.")

        qs = SubSubCategory.objects.filter(name=value, subcategory=subcat)

        if qs.count() == 1:
            return qs.first()

        if qs.count() > 1:
            raise ValueError(
                f"❌ Multiple SubSubCategories named '{value}' under subcategory '{subcategory_name}'."
            )

        raise ValueError(
            f"❌ SubSubCategory '{value}' under subcategory '{subcategory_name}' does not exist."
        )


# =====================================================
# IMPORT/EXPORT RESOURCES (ALL MODELS)
# =====================================================

class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category
        import_id_fields = ['name']
        fields = ('name', 'description')


class SubCategoryResource(resources.ModelResource):
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(Category, 'name')
    )

    class Meta:
        model = SubCategory
        import_id_fields = ['name']
        fields = ('name', 'category', 'description')


class SubSubCategoryResource(resources.ModelResource):
    subcategory = fields.Field(
        column_name='subcategory',
        attribute='subcategory',
        widget=ForeignKeyWidget(SubCategory, 'name')
    )

    class Meta:
        model = SubSubCategory
        import_id_fields = ['name', 'subcategory']
        fields = ('name', 'subcategory', 'description')


class SupplierResource(resources.ModelResource):
    class Meta:
        model = Supplier
        import_id_fields = ['company_name']
        fields = ('company_name', 'phone', 'is_active')


class CustomerResource(resources.ModelResource):
    class Meta:
        model = Customer
        import_id_fields = ['company_name']
        fields = ('company_name', 'phone', 'is_active')


class ProductResource(resources.ModelResource):
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(Category, 'name')
    )
    subcategory = fields.Field(
        column_name='subcategory',
        attribute='subcategory',
        widget=ForeignKeyWidget(SubCategory, 'name')
    )
    subsubcategory = fields.Field(
        column_name='subsubcategory',
        attribute='subsubcategory',
        widget=SubSubCategoryCompositeWidget(SubSubCategory, 'name')
    )

    class Meta:
        model = Product
        import_id_fields = ['code']
        fields = (
            'code', 'name', 'description',
            'category', 'subcategory', 'subsubcategory',
            'unit_price', 'current_stock', 'minimum_stock', 'is_active'
        )


# =====================================================
# ADMIN REGISTRATION (ALL MODELS)
# =====================================================

@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin):
    resource_class = CategoryResource
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']
    ordering = ['name']


@admin.register(SubCategory)
class SubCategoryAdmin(ImportExportModelAdmin):
    resource_class = SubCategoryResource
    list_display = ['name', 'category', 'description', 'created_at']
    search_fields = ['name', 'category__name']
    list_filter = ['category']
    ordering = ['category', 'name']
    autocomplete_fields = ['category']


@admin.register(SubSubCategory)
class SubSubCategoryAdmin(ImportExportModelAdmin):
    resource_class = SubSubCategoryResource
    list_display = ['name', 'subcategory', 'get_category', 'description', 'created_at']
    search_fields = ['name', 'subcategory__name', 'subcategory__category__name']  # <-- FIXED
    list_filter = ['subcategory__category', 'subcategory', 'created_at']
    ordering = ['subcategory__category', 'subcategory', 'name']
    autocomplete_fields = ['subcategory']

    def get_category(self, obj):
        return obj.subcategory.category.name
    get_category.short_description = 'Category'



@admin.register(Supplier)
class SupplierAdmin(ImportExportModelAdmin):
    resource_class = SupplierResource
    list_display = ['company_name', 'phone', 'is_active', 'created_at']
    search_fields = ['company_name', 'phone']
    list_filter = ['is_active']
    ordering = ['company_name']


@admin.register(Customer)
class CustomerAdmin(ImportExportModelAdmin):
    resource_class = CustomerResource
    list_display = ['company_name', 'phone', 'is_active', 'created_at']
    search_fields = ['company_name', 'phone']
    ordering = ['company_name']


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = [
        'code', 'name', 'category', 'subcategory', 'subsubcategory',
        'unit_price', 'current_stock', 'minimum_stock', 'is_active'
    ]
    search_fields = ['code', 'name']
    list_filter = ['category', 'subcategory', 'subsubcategory', 'is_active']
    autocomplete_fields = ['category', 'subcategory', 'subsubcategory']


# =====================================================
# NON-IMPORT MODELS (STOCK, SALES, AUDIT)
# =====================================================

@admin.register(MonthlyOpeningStock)
class MonthlyOpeningStockAdmin(admin.ModelAdmin):
    list_display = ['product', 'month', 'opening_quantity', 'recorded_by', 'recorded_at']
    search_fields = ['product__code', 'product__name']
    list_filter = ['month']
    autocomplete_fields = ['product', 'recorded_by']


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ['product', 'entry_type', 'quantity', 'supplier', 'recorded_by', 'created_at']
    search_fields = ['product__code', 'product__name']
    list_filter = ['entry_type']
    autocomplete_fields = ['product', 'supplier', 'recorded_by']
    readonly_fields = ['created_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'description', 'ip_address', 'timestamp']
    search_fields = ['action', 'user__username']
    list_filter = ['action']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']


class SaleLineItemInline(admin.TabularInline):
    model = SaleLineItem
    extra = 0
    readonly_fields = ['subtotal']
    autocomplete_fields = ['product']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'sale_number', 'customer', 'total_amount', 'mode_of_payment',
        'amount_paid', 'outstanding_balance', 'created_at'
    ]
    search_fields = ['sale_number', 'customer__company_name']
    list_filter = ['mode_of_payment']
    autocomplete_fields = ['customer', 'recorded_by']
    readonly_fields = ['sale_number', 'total_amount', 'outstanding_balance', 'created_at', 'updated_at']
    inlines = [SaleLineItemInline]


@admin.register(SaleLineItem)
class SaleLineItemAdmin(admin.ModelAdmin):
    list_display = [
        'sale', 'product', 'quantity_ordered', 'quantity_supplied',
        'supply_status', 'unit_price', 'subtotal'
    ]
    search_fields = ['sale__sale_number', 'product__code']
    list_filter = ['supply_status']
    autocomplete_fields = ['sale', 'product']
    readonly_fields = ['subtotal']
