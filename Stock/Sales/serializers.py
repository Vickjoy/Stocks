# serializers.py
from rest_framework import serializers
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from .models import (
    UserProfile, Category, SubCategory, SubSubCategory, ProductGroup, Supplier, Customer, Product, 
    Salesperson,MonthlyOpeningStock, StockEntry, AuditLog, Sale, SaleLineItem, StockMovement, DeliveryRecord
)

# ========================
# User Serializers
# ========================
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['role']


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'role', 'is_staff', 'is_superuser']
        read_only_fields = ['id']

    def get_role(self, obj):
        try:
            return obj.profile.role
        except UserProfile.DoesNotExist:
            return 'staff'


class UserDetailSerializer(serializers.ModelSerializer):
    groups = serializers.StringRelatedField(many=True, read_only=True)
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'is_staff', 'is_superuser',
            'groups', 'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

    def get_role(self, obj):
        try:
            return obj.profile.role
        except UserProfile.DoesNotExist:
            return 'staff'

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
    group_name = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'code', 'name', 'description',
            'category', 'category_name',
            'subcategory', 'subcategory_name',
            'subsubcategory', 'subsubcategory_name',
            'group', 'group_name',
            'unit_price', 'current_stock', 'minimum_stock',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_group_name(self, obj):
        return obj.get_group_name()

    def validate(self, data):
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
    outstanding_invoices = serializers.IntegerField()
    outstanding_sales = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_outstanding = serializers.DecimalField(max_digits=12, decimal_places=2)
    stock_entries_count = serializers.IntegerField()
    monthly_sales = serializers.ListField(child=serializers.DictField())
    top_products = serializers.ListField(child=serializers.DictField())


# ========================
# Monthly Sales Serializer
# ========================
class MonthlySalesSerializer(serializers.Serializer):
    month = serializers.CharField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)


# ========================
# Top Products Serializer
# ========================
class TopProductSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.IntegerField()


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

        # Stock check removed — stock is only checked and deducted on approval
        return data


class SaleSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.company_name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    line_items = SaleLineItemSerializer(many=True, read_only=True)
    has_outstanding = serializers.SerializerMethodField()
    is_fully_paid = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            'id', 'sale_number', 'customer', 'customer_name',
            'sale_date',
            'lpo_quotation_number', 'delivery_number',
            'mode_of_payment', 'subtotal', 'vat_amount', 'total_amount',
            'amount_paid', 'outstanding_balance',
            'status', 'approved_by', 'approved_by_name',
            'approved_at', 'rejection_reason',
            'line_items', 'has_outstanding', 'is_fully_paid',
            'recorded_by', 'salesperson', 'recorded_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'sale_number', 'outstanding_balance',
            'approved_by', 'approved_at',
            'created_at', 'updated_at'
        ]

    def get_has_outstanding(self, obj):
        return obj.has_outstanding_supplies()

    def get_is_fully_paid(self, obj):
        return obj.is_fully_paid()


class SaleCreateSerializer(serializers.ModelSerializer):
    line_items = SaleLineItemSerializer(many=True)

    # Accept customer_name as a fallback when no FK is provided
    customer_name = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Provide this when the customer was typed manually and not selected from the dropdown."
    )
    # Accept sale_date from the modal
    sale_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="The date the sale took place, as entered by staff."
    )

    class Meta:
        model = Sale
        fields = [
            'customer',           # optional when customer_name is supplied
            'customer_name',      # write-only fallback
            'sale_date',          # optional explicit sale date
            'lpo_quotation_number', 'delivery_number',
            'mode_of_payment', 'subtotal', 'vat_amount', 'total_amount',
            'amount_paid', 'line_items', 'salesperson'
        ]
        extra_kwargs = {
            # Make customer optional at field level; we enforce it in validate()
            'customer': {'required': False},
        }

    def validate(self, data):
        # ── Resolve customer ─────────────────────────────────────────────────
        customer = data.get('customer')
        customer_name = data.pop('customer_name', None)  # remove from data; not a model field

        if not customer:
            if not customer_name or not customer_name.strip():
                raise serializers.ValidationError(
                    {'customer': 'A customer is required. Please select one from the list or type a valid name.'}
                )
            # Try to find an existing customer first; create one if not found
            customer_obj, created = Customer.objects.get_or_create(
                company_name__iexact=customer_name.strip(),
                defaults={'company_name': customer_name.strip()}
            )
            data['customer'] = customer_obj
        # ─────────────────────────────────────────────────────────────────────

        # ── Payment validation ────────────────────────────────────────────────
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
        # ─────────────────────────────────────────────────────────────────────

        # ── Line items ────────────────────────────────────────────────────────
        line_items = data.get('line_items', [])
        if not line_items:
            raise serializers.ValidationError({
                'line_items': 'At least one product must be added to the sale'
            })
        # ─────────────────────────────────────────────────────────────────────

        # ── Financial cross-checks ────────────────────────────────────────────
        subtotal = data.get('subtotal', 0)
        vat_amount = data.get('vat_amount', 0)
        total_amount = data.get('total_amount', 0)

        data['subtotal'] = Decimal(str(subtotal)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        data['vat_amount'] = Decimal(str(vat_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        data['total_amount'] = Decimal(str(total_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        expected_vat = (data['subtotal'] * Decimal('0.16')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if abs(data['vat_amount'] - expected_vat) > Decimal('0.02'):
            raise serializers.ValidationError({
                'vat_amount': f'VAT amount should be 16% of subtotal. Expected: {expected_vat}, Got: {data["vat_amount"]}'
            })

        expected_total = (data['subtotal'] + data['vat_amount']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if abs(data['total_amount'] - expected_total) > Decimal('0.02'):
            raise serializers.ValidationError({
                'total_amount': f'Total should equal subtotal + VAT. Expected: {expected_total}, Got: {data["total_amount"]}'
            })
        # ─────────────────────────────────────────────────────────────────────

        return data

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items')
        validated_data['recorded_by'] = self.context['request'].user
        validated_data['status'] = 'pending'

        sale = Sale.objects.create(**validated_data)

        for item_data in line_items_data:
            SaleLineItem.objects.create(sale=sale, **item_data)

        sale.calculate_total()
        return sale


# ========================
# Sale Approval Serializer
# ========================
class SaleApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data['action'] == 'reject' and not data.get('rejection_reason', '').strip():
            raise serializers.ValidationError({
                'rejection_reason': 'A reason is required when rejecting a sale.'
            })
        return data


# ========================
# Delivery Serializers
# ========================
class DeliveryLineItemSerializer(serializers.Serializer):
    line_item_id = serializers.IntegerField()
    quantity_delivered = serializers.IntegerField(min_value=1)


class DeliveryRecordCreateSerializer(serializers.Serializer):
    delivery_date = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True)
    items = DeliveryLineItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('At least one item is required.')
        return value


class DeliveryRecordSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(
        source='recorded_by.get_full_name', read_only=True
    )
    delivery_items = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryRecord
        fields = [
            'id', 'sale', 'delivery_date', 'notes',
            'recorded_by', 'recorded_by_name',
            'delivery_items', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_delivery_items(self, obj):
        return [
            {
                'product_code': item.line_item.product.code,
                'product_name': item.line_item.product.name,
                'quantity_delivered': item.quantity_delivered,
            }
            for item in obj.delivery_items.select_related(
                'line_item__product'
            ).all()
        ]


# ========================
# Password Reset Serializers
# ========================
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        """Check if user with this email exists"""
        # Don't raise error - just validate format
        # This prevents revealing which emails are registered (security)
        return value

    def save(self):
        email = self.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Return success even if user doesn't exist (security best practice)
            return {'message': 'If an account exists, a reset link has been sent.'}
        
        # Generate password reset token
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build reset URL
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
        
        # Send email with HTML formatting
        subject = 'Password Reset Request - Edge Systems Inventory'
        message = f"""
Hello {user.username},

You have requested to reset your password for Edge Systems Inventory.

Click the link below to reset your password:
{reset_url}

This link will expire in 24 hours.

If you did not request this password reset, please ignore this email.

---
Edge Systems
Inventory Management System
        """
        
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
        .button {{ display: inline-block; padding: 12px 30px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; background-color: #f4f4f4; border-radius: 0 0 5px 5px; }}
        .warning {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🔐 Edge Systems Inventory</h2>
        </div>
        <div class="content">
            <h3>Password Reset Request</h3>
            <p>Hello <strong>{user.username}</strong>,</p>
            <p>You have requested to reset your password for Edge Systems Inventory Management System.</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">Reset Your Password</a>
            </p>
            <p style="font-size: 12px; color: #666; word-wrap: break-word;">
                Or copy this link: <br>{reset_url}
            </p>
            <div class="warning">
                <strong>⏰ Important:</strong> This link will expire in 24 hours.
            </div>
            <p style="font-size: 13px; color: #666;">
                If you did not request this password reset, please ignore this email. Your password will remain unchanged.
            </p>
        </div>
        <div class="footer">
            <p>© 2025 Edge Systems. All rights reserved.</p>
            <p>This is an automated message, please do not reply.</p>
        </div>
    </div>
</body>
</html>
        """
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            raise serializers.ValidationError("Failed to send reset email. Please try again later.")
        
        return {'message': 'Password reset link has been sent to your email.'}


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        """Validate passwords match and token is valid"""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        # Validate token
        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"token": "Invalid reset link."})
        
        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, data['token']):
            raise serializers.ValidationError({"token": "Invalid or expired reset link."})
        
        data['user'] = user
        return data

    def save(self):
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        return {'message': 'Password has been reset successfully.'}


# ========================
# Stock Movement Serializer
# ========================
class StockMovementSerializer(serializers.ModelSerializer):
    """
    Serializer for the StockMovement model with direction and reason tracking
    """
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    subcategory_name = serializers.CharField(source='product.subcategory.name', read_only=True)
    subsubcategory_name = serializers.CharField(source='product.subsubcategory.name', read_only=True)
    
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    sale_number = serializers.CharField(source='sale.sale_number', read_only=True)
    customer_name = serializers.CharField(source='sale.customer.company_name', read_only=True)
    
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    
    direction_display = serializers.CharField(source='get_direction_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = [
            'id', 'product', 'product_code', 'product_name',
            'category_name', 'subcategory_name', 'subsubcategory_name',
            'direction', 'direction_display',
            'reason', 'reason_display',
            'quantity',
            'supplier', 'supplier_name',
            'sale', 'sale_number', 'customer_name',
            'notes',
            'recorded_by', 'recorded_by_name',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        """Validate direction matches reason"""
        direction = data.get('direction')
        reason = data.get('reason')
        
        if reason in ['RESTOCK', 'ADJUSTMENT', 'INITIAL', 'RETURN']:
            if direction != 'IN':
                raise serializers.ValidationError({
                    'direction': f'Reason {reason} must have direction IN'
                })
        
        if reason in ['SALE', 'DAMAGE', 'TRANSFER']:
            if direction != 'OUT':
                raise serializers.ValidationError({
                    'direction': f'Reason {reason} must have direction OUT'
                })
        
        return data

# ========================
# Salesperson Serializer
# ========================
class SalespersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Salesperson
        fields = ['id', 'name', 'phone', 'email', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']