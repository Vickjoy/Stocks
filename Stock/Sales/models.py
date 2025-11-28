# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP


class Category(models.Model):
    """Main product categories (Fire, ICT, Solar)"""
    CATEGORY_CHOICES = [
        ('Fire', 'Fire'),
        ('ICT', 'ICT'),
        ('Solar', 'Solar'),
    ]
    
    name = models.CharField(max_length=50, unique=True, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class SubCategory(models.Model):
    """Subcategories under main categories"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "SubCategories"
        unique_together = ('category', 'name')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"


class SubSubCategory(models.Model):
    """Sub-subcategories under subcategories (e.g., Panels, Detectors, I/O Modules)"""
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='subsubcategories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Sub-SubCategories"
        unique_together = ('subcategory', 'name')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.subcategory.category.name} - {self.subcategory.name} - {self.name}"


class ProductGroup(models.Model):
    """Product groups under subcategories - DEPRECATED, use SubSubCategory instead"""
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='groups')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Product Groups (Deprecated)"
        unique_together = ('subcategory', 'name')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.subcategory.name} - {self.name}"


class Supplier(models.Model):
    """Track suppliers/vendors - Simplified"""
    company_name = models.CharField(max_length=200, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.company_name


class Customer(models.Model):
    """Track customers/buyers - Simplified"""
    company_name = models.CharField(max_length=200, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.company_name


class Product(models.Model):
    """Products/Stock items - Updated with hierarchical categories"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='products')
    subsubcategory = models.ForeignKey(
        SubSubCategory, 
        on_delete=models.SET_NULL, 
        related_name='products', 
        null=True, 
        blank=True,
        help_text="Product group - optional grouping within subcategory"
    )
    
    group = models.ForeignKey(
        ProductGroup, 
        on_delete=models.SET_NULL, 
        related_name='products', 
        null=True, 
        blank=True,
        help_text="DEPRECATED: Use subsubcategory instead"
    )
    
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    current_stock = models.IntegerField(null=True, blank=True, default=0)
    minimum_stock = models.IntegerField(null=True, blank=True, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_group_name(self):
        """Returns the group name from subsubcategory (preferred) or deprecated group field"""
        if self.subsubcategory:
            return self.subsubcategory.name
        elif self.group:
            return self.group.name
        return "Ungrouped"


class MonthlyOpeningStock(models.Model):
    """Track opening stock for each month"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='monthly_opening')
    month = models.DateField()
    opening_quantity = models.IntegerField()
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('product', 'month')
    
    def __str__(self):
        return f"{self.product.code} - {self.month.strftime('%B %Y')}"


class StockEntry(models.Model):
    """Log all stock movements"""
    ENTRY_TYPE_CHOICES = [
        ('In', 'Stock In'),
        ('Out', 'Stock Out'),
        ('Adjustment', 'Adjustment'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_entries')
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE_CHOICES)
    quantity = models.IntegerField()
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.product.code} - {self.entry_type} - {self.quantity}"


class AuditLog(models.Model):
    """Track critical actions for security/audit"""
    ACTION_CHOICES = [
        ('Stock Edit', 'Stock Edit'),
        ('Sale Created', 'Sale Created'),
        ('Sale Updated', 'Sale Updated'),
        ('Supply Update', 'Supply Update'),
    ]
    
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} - {self.user} - {self.timestamp}"


class Sale(models.Model):
    """Track sales with multiple products and payment details"""
    PAYMENT_MODE_CHOICES = [
        ('Cash', 'Cash'),
        ('Cheque', 'Cheque'),
        ('Mpesa', 'Mpesa'),
        ('Not Paid', 'Not Paid'),
    ]

    sale_number = models.CharField(max_length=50, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')
    lpo_quotation_number = models.CharField(max_length=100, blank=True)
    delivery_number = models.CharField(max_length=100, blank=True)
    mode_of_payment = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, default='Not Paid')
    
    # Financial fields with VAT
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Sum of all products (before VAT)")
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="16% VAT on subtotal")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Subtotal + VAT")
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Amount paid by customer")
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total - Amount Paid")
    
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Sale-{self.sale_number} - {self.customer.company_name if self.customer else 'N/A'}"

    def save(self, *args, **kwargs):
        # Generate sale number if not exists
        if not self.sale_number:
            today_str = timezone.now().strftime('%Y%m%d')
            prefix = f"S{today_str}"
            today_sales_count = Sale.objects.filter(sale_number__startswith=prefix).count() + 1
            sequence = str(today_sales_count).zfill(2)
            self.sale_number = f"{prefix}{sequence}"

        # Reset amount paid if Not Paid
        if self.mode_of_payment == 'Not Paid':
            self.amount_paid = Decimal('0.00')
        
        # Ensure all decimal values are properly rounded
        self.subtotal = Decimal(str(self.subtotal)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.vat_amount = Decimal(str(self.vat_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.total_amount = Decimal(str(self.total_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.amount_paid = Decimal(str(self.amount_paid)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Calculate outstanding balance (Total - Paid)
        self.outstanding_balance = (self.total_amount - self.amount_paid).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if self.outstanding_balance < 0:
            self.outstanding_balance = Decimal('0.00')

        super().save(*args, **kwargs)

    def calculate_total(self):
        """Calculate subtotal, VAT, and total from line items using Decimal precision"""
        # Calculate subtotal from line items
        subtotal = Decimal('0.00')
        for item in self.line_items.all():
            item_subtotal = Decimal(str(item.subtotal)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            subtotal += item_subtotal
        
        self.subtotal = subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Calculate VAT (16% of subtotal)
        self.vat_amount = (self.subtotal * Decimal('0.16')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Calculate total (subtotal + VAT)
        self.total_amount = (self.subtotal + self.vat_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        self.save()
        return self.total_amount

    def has_outstanding_supplies(self):
        """Check if any line items have outstanding quantities"""
        return self.line_items.filter(
            models.Q(supply_status='Not Supplied') |
            models.Q(supply_status='Partially Supplied')
        ).exists()
    
    def is_fully_paid(self):
        """Check if sale is fully paid"""
        return self.outstanding_balance == Decimal('0.00')


class SaleLineItem(models.Model):
    """Individual products in a sale"""
    SUPPLY_STATUS_CHOICES = [
        ('Supplied', 'Supplied'),
        ('Partially Supplied', 'Partially Supplied'),
        ('Not Supplied', 'Not Supplied'),
    ]

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='line_items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')
    quantity_ordered = models.IntegerField()
    quantity_supplied = models.IntegerField(default=0)
    supply_status = models.CharField(max_length=20, choices=SUPPLY_STATUS_CHOICES, default='Supplied')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.sale.sale_number} - {self.product.code if self.product else 'N/A'}"

    def outstanding_quantity(self):
        ordered = self.quantity_ordered or 0
        supplied = self.quantity_supplied or 0
        return ordered - supplied

    def save(self, *args, **kwargs):
        if self.quantity_ordered is None:
            self.quantity_ordered = 0
        if self.quantity_supplied is None:
            self.quantity_supplied = 0

        # Calculate subtotal (quantity * unit price)
        unit_price = Decimal(str(self.unit_price or 0))
        quantity = Decimal(str(self.quantity_ordered))
        self.subtotal = (unit_price * quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        is_new = self.pk is None
        old_supplied = 0
        if not is_new:
            try:
                old_item = SaleLineItem.objects.get(pk=self.pk)
                old_supplied = old_item.quantity_supplied
            except SaleLineItem.DoesNotExist:
                pass

        # Handle stock adjustments based on supply status
        if self.product:
            if self.supply_status == 'Supplied':
                self.quantity_supplied = self.quantity_ordered
                if is_new and self.quantity_supplied > 0:
                    self.product.current_stock -= self.quantity_supplied
                    self.product.save()

            elif self.supply_status == 'Partially Supplied':
                if self.pk:
                    diff = self.quantity_supplied - old_supplied
                    if diff > 0:
                        self.product.current_stock -= diff
                        self.product.save()
                else:
                    if self.quantity_supplied > 0:
                        self.product.current_stock -= self.quantity_supplied
                        self.product.save()

            elif self.supply_status == 'Not Supplied':
                self.quantity_supplied = 0

        super().save(*args, **kwargs)

        # Create stock entry for supplied items
        if is_new and self.supply_status in ['Supplied', 'Partially Supplied'] and self.quantity_supplied > 0:
            StockEntry.objects.create(
                product=self.product,
                entry_type='Out',
                quantity=self.quantity_supplied,
                notes=f"Sale #{self.sale.sale_number} to {self.sale.customer.company_name}",
                recorded_by=self.sale.recorded_by
            )