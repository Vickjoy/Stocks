# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')
    is_director = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Category(models.Model):
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
    company_name = models.CharField(max_length=200, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name


class Customer(models.Model):
    company_name = models.CharField(max_length=200, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='products')
    subsubcategory = models.ForeignKey(
        SubSubCategory, on_delete=models.SET_NULL,
        related_name='products', null=True, blank=True,
        help_text="Product group - optional grouping within subcategory"
    )
    group = models.ForeignKey(
        ProductGroup, on_delete=models.SET_NULL,
        related_name='products', null=True, blank=True,
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
        if self.subsubcategory:
            return self.subsubcategory.name
        elif self.group:
            return self.group.name
        return "Ungrouped"


class MonthlyOpeningStock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='monthly_opening')
    month = models.DateField()
    opening_quantity = models.IntegerField()
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'month')

    def __str__(self):
        return f"{self.product.code} - {self.month.strftime('%B %Y')}"


class StockMovement(models.Model):
    DIRECTION_CHOICES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    ]
    REASON_CHOICES = [
        ('RESTOCK', 'Restocking from Supplier'),
        ('ADJUSTMENT', 'Manual Stock Adjustment'),
        ('INITIAL', 'Initial Stock Entry'),
        ('RETURN', 'Customer Return'),
        ('SALE', 'Sale/Delivery'),
        ('DAMAGE', 'Damaged/Lost Stock'),
        ('TRANSFER', 'Stock Transfer'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    quantity = models.IntegerField()
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    sale = models.ForeignKey('Sale', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['direction', 'reason']),
            models.Index(fields=['product', 'created_at']),
        ]

    def __str__(self):
        return f"{self.product.code} - {self.direction} ({self.reason}) - {self.quantity}"

    def save(self, *args, **kwargs):
        if self.reason in ['RESTOCK', 'ADJUSTMENT', 'INITIAL', 'RETURN']:
            if self.direction != 'IN':
                raise ValueError(f"Reason {self.reason} must have direction IN")
        if self.reason in ['SALE', 'DAMAGE', 'TRANSFER']:
            if self.direction != 'OUT':
                raise ValueError(f"Reason {self.reason} must have direction OUT")
        super().save(*args, **kwargs)


class StockEntry(models.Model):
    """DEPRECATED: Legacy stock entry model - use StockMovement instead"""
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

    class Meta:
        verbose_name_plural = "Stock Entries (Legacy)"

    def __str__(self):
        return f"{self.product.code} - {self.entry_type} - {self.quantity}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('Stock Edit', 'Stock Edit'),
        ('Sale Created', 'Sale Created'),
        ('Sale Updated', 'Sale Updated'),
        ('Sale Approved', 'Sale Approved'),
        ('Sale Rejected', 'Sale Rejected'),
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
    PAYMENT_MODE_CHOICES = [
        ('Cash', 'Cash'),
        ('Cheque', 'Cheque'),
        ('Mpesa', 'Mpesa'),
        ('Not Paid', 'Not Paid'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    sale_number = models.CharField(max_length=50, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')

    sale_date = models.DateField(
        null=True, blank=True,
        help_text="The date the sale took place (set by staff at time of recording)"
    )

    lpo_quotation_number = models.CharField(max_length=100, blank=True)
    delivery_number = models.CharField(max_length=100, blank=True)
    mode_of_payment = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, default='Not Paid')

    # Financial fields
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_date = models.DateField(null=True, blank=True)
    payment_note = models.TextField(blank=True, default='')

    # VAT applicability — set by admin at approval time
    vat_applied = models.BooleanField(
        default=False,
        help_text="Whether 16% VAT was applied to this sale. Set by admin when approving."
    )

    # Status and approval tracking fields
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="pending = awaiting admin approval, approved = stock deducted, rejected = sale cancelled"
    )
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_sales'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    salesperson = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Sale-{self.sale_number} - {self.customer.company_name if self.customer else 'N/A'}"

    def save(self, *args, **kwargs):
        if not self.sale_number:
            today_str = timezone.now().strftime('%Y%m%d')
            prefix = f"S{today_str}"
            today_sales_count = Sale.objects.filter(sale_number__startswith=prefix).count() + 1
            self.sale_number = f"{prefix}{str(today_sales_count).zfill(2)}"

        if self.mode_of_payment == 'Not Paid':
            self.amount_paid = Decimal('0.00')

        self.subtotal = Decimal(str(self.subtotal)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.vat_amount = Decimal(str(self.vat_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.total_amount = Decimal(str(self.total_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.amount_paid = Decimal(str(self.amount_paid)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.outstanding_balance = (self.total_amount - self.amount_paid).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        if self.outstanding_balance < 0:
            self.outstanding_balance = Decimal('0.00')

        super().save(*args, **kwargs)

    def calculate_total(self):
        """
        Recalculates subtotal from line items.
        VAT is only added if vat_applied is True.
        """
        subtotal = Decimal('0.00')
        for item in self.line_items.all():
            subtotal += Decimal(str(item.subtotal)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.subtotal = subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if self.vat_applied:
            self.vat_amount = (self.subtotal * Decimal('0.16')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        else:
            self.vat_amount = Decimal('0.00')

        self.total_amount = (self.subtotal + self.vat_amount).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        self.save()
        return self.total_amount

    def has_outstanding_supplies(self):
        return self.line_items.filter(
            models.Q(supply_status='Not Supplied') |
            models.Q(supply_status='Partially Supplied')
        ).exists()

    def is_fully_paid(self):
        return self.outstanding_balance == Decimal('0.00')

    def deduct_stock(self, approved_by_user):
        for item in self.line_items.all():
            if item.supply_status in ['Supplied', 'Partially Supplied'] and item.quantity_supplied > 0:
                item.product.current_stock -= item.quantity_supplied
                item.product.save()

                StockMovement.objects.create(
                    product=item.product,
                    direction='OUT',
                    reason='SALE',
                    quantity=item.quantity_supplied,
                    sale=self,
                    notes=f"Approved sale #{self.sale_number} to {self.customer.company_name}",
                    recorded_by=approved_by_user
                )


class SaleLineItem(models.Model):
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
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True, default=0
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.sale.sale_number} - {self.product.code if self.product else 'N/A'}"

    def outstanding_quantity(self):
        return (self.quantity_ordered or 0) - (self.quantity_supplied or 0)

    def save(self, *args, **kwargs):
        if self.quantity_ordered is None:
            self.quantity_ordered = 0
        if self.quantity_supplied is None:
            self.quantity_supplied = 0

        unit_price = Decimal(str(self.unit_price or 0))
        quantity = Decimal(str(self.quantity_ordered))
        self.subtotal = (unit_price * quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if self.supply_status == 'Supplied':
            self.quantity_supplied = self.quantity_ordered
        elif self.supply_status == 'Not Supplied':
            self.quantity_supplied = 0

        super().save(*args, **kwargs)


class DeliveryRecord(models.Model):
    sale = models.ForeignKey(
        Sale, on_delete=models.CASCADE, related_name='delivery_records'
    )
    delivery_date = models.DateField()
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-delivery_date']

    def __str__(self):
        return f"Delivery for {self.sale.sale_number} on {self.delivery_date}"


class DeliveryLineItem(models.Model):
    delivery = models.ForeignKey(
        DeliveryRecord, on_delete=models.CASCADE, related_name='delivery_items'
    )
    line_item = models.ForeignKey(
        SaleLineItem, on_delete=models.CASCADE, related_name='delivery_records'
    )
    quantity_delivered = models.IntegerField()

    def __str__(self):
        return f"{self.line_item.product.code} — {self.quantity_delivered} delivered"


class Salesperson(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name