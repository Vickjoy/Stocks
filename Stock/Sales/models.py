# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"


class Supplier(models.Model):
    """Track suppliers/vendors"""
    company_name = models.CharField(max_length=200, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.company_name


class Customer(models.Model):
    """Track customers/buyers"""
    PAYMENT_TYPE_CHOICES = [
        ('Cash', 'Cash'),
        ('Cheque', 'Cheque'),
        ('Credit', 'Credit'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Mobile Money', 'Mobile Money'),
    ]
    
    company_name = models.CharField(max_length=200, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.company_name


class Product(models.Model):
    """Products/Stock items"""
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='products')
    code = models.CharField(max_length=50, unique=True)  # e.g., CAP320
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    current_stock = models.IntegerField(null=True, blank=True, default=0)
    minimum_stock = models.IntegerField(null=True, blank=True, default=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class MonthlyOpeningStock(models.Model):
    """Track opening stock for each month"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='monthly_opening')
    month = models.DateField()  # First day of month
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


class Invoice(models.Model):
    """Invoice management"""
    INVOICE_STATUS_CHOICES = [
        ('Outstanding', 'Outstanding'),
        ('Partial', 'Partial Payment'),
        ('Paid', 'Fully Paid'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='Outstanding')
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"INV-{self.invoice_number}"
    
    def remaining_balance(self):
        return self.total_amount - self.paid_amount


class InvoiceItem(models.Model):
    """Individual items in an invoice"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.product.code}"


class Payment(models.Model):
    """Track invoice payments"""
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Cheque', 'Cheque'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Mobile Money', 'Mobile Money'),
        ('Other', 'Other'),
    ]
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True)
    payment_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Payment for {self.invoice.invoice_number} - {self.amount}"


class LPO(models.Model):
    """Local Purchase Order - Track partial supplies"""
    LPO_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Partial', 'Partially Delivered'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    lpo_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='lpos')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='lpos')
    ordered_quantity = models.IntegerField()
    delivered_quantity = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=LPO_STATUS_CHOICES, default='Pending')
    order_date = models.DateField(default=timezone.now)
    expected_delivery = models.DateField(null=True, blank=True)
    actual_delivery = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def pending_quantity(self):
        return self.ordered_quantity - self.delivered_quantity
    
    def __str__(self):
        return f"LPO-{self.lpo_number}"


class AuditLog(models.Model):
    """Track critical actions for security/audit"""
    ACTION_CHOICES = [
        ('Stock Edit', 'Stock Edit'),
        ('Invoice Created', 'Invoice Created'),
        ('Invoice Updated', 'Invoice Updated'),
        ('Payment Recorded', 'Payment Recorded'),
        ('LPO Updated', 'LPO Updated'),
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
    
# Add this to your existing models.py

class Sale(models.Model):
    """Track individual sales with supply status"""
    SUPPLY_STATUS_CHOICES = [
        ('Supplied', 'Supplied'),
        ('Partially Supplied', 'Partially Supplied'),
        ('Not Supplied', 'Not Supplied'),
    ]
    
    sale_number = models.CharField(max_length=50, unique=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sales')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')
    
    # Quantity fields
    quantity_ordered = models.IntegerField()
    quantity_supplied = models.IntegerField(default=0)
    supply_status = models.CharField(max_length=20, choices=SUPPLY_STATUS_CHOICES)
    
    # Pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # References
    lpo_quotation_number = models.CharField(max_length=100, blank=True)
    delivery_number = models.CharField(max_length=100, blank=True)
    
    # Metadata
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Sale-{self.sale_number} - {self.product.code if self.product else 'N/A'}"
    
    def outstanding_quantity(self):
        """Calculate outstanding quantity"""
        # Handle None values for new unsaved instances
        ordered = self.quantity_ordered or 0
        supplied = self.quantity_supplied or 0
        return ordered - supplied
    
    def save(self, *args, **kwargs):
        # Ensure quantities are not None
        if self.quantity_ordered is None:
            self.quantity_ordered = 0
        if self.quantity_supplied is None:
            self.quantity_supplied = 0
        
        # Auto-generate sale number if not exists
        if not self.sale_number:
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            import random
            self.sale_number = f"S{timestamp}{random.randint(10, 99)}"
        
        # Calculate total amount
        unit_price = self.unit_price or 0
        self.total_amount = self.quantity_ordered * unit_price
        
        # Check if this is a new sale
        is_new = self.pk is None
        
        # Update product stock if supplied
        if self.product:
            if self.supply_status == 'Supplied':
                self.quantity_supplied = self.quantity_ordered
                if is_new and self.quantity_supplied > 0:
                    self.product.current_stock -= self.quantity_supplied
                    self.product.save()
            elif self.supply_status == 'Partially Supplied' and self.quantity_supplied > 0:
                # Only deduct what was actually supplied
                if self.pk:  # If updating existing sale
                    old_sale = Sale.objects.get(pk=self.pk)
                    diff = self.quantity_supplied - old_sale.quantity_supplied
                    if diff > 0:
                        self.product.current_stock -= diff
                        self.product.save()
                else:  # New sale
                    self.product.current_stock -= self.quantity_supplied
                    self.product.save()
            elif self.supply_status == 'Not Supplied':
                self.quantity_supplied = 0
            # For 'Not Supplied', don't deduct stock
        
        super().save(*args, **kwargs)
        
        # Create stock entry log (only for new sales with supplied items)
        if is_new and self.supply_status in ['Supplied', 'Partially Supplied'] and self.quantity_supplied > 0:
            StockEntry.objects.create(
                product=self.product,
                entry_type='Out',
                quantity=self.quantity_supplied,
                notes=f"Sale #{self.sale_number} to {self.customer.company_name}",
                recorded_by=self.recorded_by
            )