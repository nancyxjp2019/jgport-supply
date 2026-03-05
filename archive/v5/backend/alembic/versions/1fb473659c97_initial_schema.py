from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1fb473659c97'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('business_logs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('request_id', sa.String(length=64), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('role', sa.String(length=32), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('entity_type', sa.String(length=32), nullable=True),
    sa.Column('entity_id', sa.String(length=64), nullable=True),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.Column('before_status', sa.String(length=32), nullable=True),
    sa.Column('after_status', sa.String(length=32), nullable=True),
    sa.Column('result', sa.String(length=32), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=True),
    sa.Column('ip', sa.String(length=64), nullable=True),
    sa.Column('detail_json', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_business_logs_action'), 'business_logs', ['action'], unique=False)
    op.create_index(op.f('ix_business_logs_created_at'), 'business_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_business_logs_entity_id'), 'business_logs', ['entity_id'], unique=False)
    op.create_index(op.f('ix_business_logs_entity_type'), 'business_logs', ['entity_type'], unique=False)
    op.create_index(op.f('ix_business_logs_order_id'), 'business_logs', ['order_id'], unique=False)
    op.create_index(op.f('ix_business_logs_request_id'), 'business_logs', ['request_id'], unique=False)
    op.create_index(op.f('ix_business_logs_result'), 'business_logs', ['result'], unique=False)
    op.create_index(op.f('ix_business_logs_role'), 'business_logs', ['role'], unique=False)
    op.create_index(op.f('ix_business_logs_user_id'), 'business_logs', ['user_id'], unique=False)
    op.create_table('inventory',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('warehouse_id', sa.Integer(), nullable=False),
    sa.Column('product_name', sa.String(length=64), nullable=False),
    sa.Column('available_qty_ton', sa.Float(), nullable=False),
    sa.Column('reserved_qty_ton', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_product_name'), 'inventory', ['product_name'], unique=False)
    op.create_index(op.f('ix_inventory_updated_at'), 'inventory', ['updated_at'], unique=False)
    op.create_index(op.f('ix_inventory_warehouse_id'), 'inventory', ['warehouse_id'], unique=False)
    op.create_table('oil_products',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_oil_products_is_active'), 'oil_products', ['is_active'], unique=False)
    op.create_index(op.f('ix_oil_products_name'), 'oil_products', ['name'], unique=True)
    op.create_table('super_admin_credentials',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('display_name', sa.String(length=128), nullable=True),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('failed_login_count', sa.Integer(), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_super_admin_credentials_is_active'), 'super_admin_credentials', ['is_active'], unique=False)
    op.create_index(op.f('ix_super_admin_credentials_username'), 'super_admin_credentials', ['username'], unique=True)
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('display_name', sa.String(length=128), nullable=True),
    sa.Column('role', sa.Enum('ADMIN', 'OPERATOR', 'CUSTOMER', 'WAREHOUSE', name='userrole', native_enum=False), nullable=False),
    sa.Column('status', sa.Enum('PENDING_ACTIVATION', 'ACTIVE', 'DISABLED', name='userstatus', native_enum=False), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_customer_id'), 'users', ['customer_id'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index(op.f('ix_users_status'), 'users', ['status'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_table('warehouses',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_warehouses_is_active'), 'warehouses', ['is_active'], unique=False)
    op.create_index(op.f('ix_warehouses_name'), 'warehouses', ['name'], unique=True)
    op.create_table('activation_codes',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activation_codes_code'), 'activation_codes', ['code'], unique=True)
    op.create_index(op.f('ix_activation_codes_user_id'), 'activation_codes', ['user_id'], unique=False)
    op.create_table('orders',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('plan_no', sa.String(length=32), nullable=False),
    sa.Column('plan_date', sa.Date(), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=True),
    sa.Column('customer_name', sa.String(length=128), nullable=True),
    sa.Column('destination_site', sa.String(length=128), nullable=False),
    sa.Column('product_name', sa.String(length=64), nullable=False),
    sa.Column('requested_qty_ton', sa.Float(), nullable=False),
    sa.Column('warehouse_id', sa.Integer(), nullable=True),
    sa.Column('unit_price', sa.Float(), nullable=True),
    sa.Column('total_amount', sa.Float(), nullable=True),
    sa.Column('status', sa.Enum('SUBMITTED', 'ACCEPTED', 'REJECTED', 'PAID_PENDING_CONFIRM', 'PAID_CONFIRMED', 'DISPATCHED', 'COMPLETED', 'CANCELLED', 'ABNORMAL_CLOSED', name='orderstatus', native_enum=False), nullable=False),
    sa.Column('payment_voucher_url', sa.String(length=512), nullable=True),
    sa.Column('bank_receipt_url', sa.String(length=512), nullable=True),
    sa.Column('dispatch_instruction_json', sa.JSON(), nullable=True),
    sa.Column('outbound_doc_url', sa.String(length=512), nullable=True),
    sa.Column('cancel_reason', sa.Text(), nullable=True),
    sa.Column('abnormal_close_reason', sa.Text(), nullable=True),
    sa.Column('abnormal_close_attachment_url', sa.String(length=512), nullable=True),
    sa.Column('completion_source', sa.Enum('WAREHOUSE', 'OPERATOR', name='completionsource', native_enum=False), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('completed_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['completed_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_created_at'), 'orders', ['created_at'], unique=False)
    op.create_index(op.f('ix_orders_created_by'), 'orders', ['created_by'], unique=False)
    op.create_index(op.f('ix_orders_customer_id'), 'orders', ['customer_id'], unique=False)
    op.create_index(op.f('ix_orders_plan_date'), 'orders', ['plan_date'], unique=False)
    op.create_index(op.f('ix_orders_plan_no'), 'orders', ['plan_no'], unique=True)
    op.create_index(op.f('ix_orders_product_name'), 'orders', ['product_name'], unique=False)
    op.create_index(op.f('ix_orders_status'), 'orders', ['status'], unique=False)
    op.create_index(op.f('ix_orders_updated_at'), 'orders', ['updated_at'], unique=False)
    op.create_index(op.f('ix_orders_warehouse_id'), 'orders', ['warehouse_id'], unique=False)
    op.create_table('super_admin_mfa',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('admin_id', sa.Integer(), nullable=False),
    sa.Column('totp_secret', sa.String(length=64), nullable=False),
    sa.Column('issuer', sa.String(length=128), nullable=False),
    sa.Column('account_label', sa.String(length=128), nullable=False),
    sa.Column('is_enabled', sa.Boolean(), nullable=False),
    sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['admin_id'], ['super_admin_credentials.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_super_admin_mfa_admin_id'), 'super_admin_mfa', ['admin_id'], unique=True)
    op.create_table('super_admin_recovery_codes',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('admin_id', sa.Integer(), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('is_used', sa.Boolean(), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['admin_id'], ['super_admin_credentials.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_super_admin_recovery_codes_admin_id'), 'super_admin_recovery_codes', ['admin_id'], unique=False)
    op.create_index(op.f('ix_super_admin_recovery_codes_code_hash'), 'super_admin_recovery_codes', ['code_hash'], unique=False)
    op.create_index(op.f('ix_super_admin_recovery_codes_is_used'), 'super_admin_recovery_codes', ['is_used'], unique=False)
    op.create_table('wechat_accounts',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('openid', sa.String(length=80), nullable=False),
    sa.Column('unionid', sa.String(length=80), nullable=True),
    sa.Column('bound_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wechat_accounts_openid'), 'wechat_accounts', ['openid'], unique=True)
    op.create_index(op.f('ix_wechat_accounts_user_id'), 'wechat_accounts', ['user_id'], unique=True)
    op.create_table('inventory_reservations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('inventory_id', sa.Integer(), nullable=False),
    sa.Column('qty_ton', sa.Float(), nullable=False),
    sa.Column('status', sa.Enum('RESERVED', 'DEDUCTED', 'RELEASED', 'REVERSED', name='inventoryreservationstatus', native_enum=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['inventory_id'], ['inventory.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_reservations_inventory_id'), 'inventory_reservations', ['inventory_id'], unique=False)
    op.create_index(op.f('ix_inventory_reservations_order_id'), 'inventory_reservations', ['order_id'], unique=False)
    op.create_index(op.f('ix_inventory_reservations_status'), 'inventory_reservations', ['status'], unique=False)
    op.create_table('order_logs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('operator_user_id', sa.Integer(), nullable=True),
    sa.Column('before_status', sa.String(length=32), nullable=True),
    sa.Column('after_status', sa.String(length=32), nullable=True),
    sa.Column('remark', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['operator_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_logs_action'), 'order_logs', ['action'], unique=False)
    op.create_index(op.f('ix_order_logs_created_at'), 'order_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_order_logs_operator_user_id'), 'order_logs', ['operator_user_id'], unique=False)
    op.create_index(op.f('ix_order_logs_order_id'), 'order_logs', ['order_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_order_logs_order_id'), table_name='order_logs')
    op.drop_index(op.f('ix_order_logs_operator_user_id'), table_name='order_logs')
    op.drop_index(op.f('ix_order_logs_created_at'), table_name='order_logs')
    op.drop_index(op.f('ix_order_logs_action'), table_name='order_logs')
    op.drop_table('order_logs')
    op.drop_index(op.f('ix_inventory_reservations_status'), table_name='inventory_reservations')
    op.drop_index(op.f('ix_inventory_reservations_order_id'), table_name='inventory_reservations')
    op.drop_index(op.f('ix_inventory_reservations_inventory_id'), table_name='inventory_reservations')
    op.drop_table('inventory_reservations')
    op.drop_index(op.f('ix_wechat_accounts_user_id'), table_name='wechat_accounts')
    op.drop_index(op.f('ix_wechat_accounts_openid'), table_name='wechat_accounts')
    op.drop_table('wechat_accounts')
    op.drop_index(op.f('ix_super_admin_recovery_codes_is_used'), table_name='super_admin_recovery_codes')
    op.drop_index(op.f('ix_super_admin_recovery_codes_code_hash'), table_name='super_admin_recovery_codes')
    op.drop_index(op.f('ix_super_admin_recovery_codes_admin_id'), table_name='super_admin_recovery_codes')
    op.drop_table('super_admin_recovery_codes')
    op.drop_index(op.f('ix_super_admin_mfa_admin_id'), table_name='super_admin_mfa')
    op.drop_table('super_admin_mfa')
    op.drop_index(op.f('ix_orders_warehouse_id'), table_name='orders')
    op.drop_index(op.f('ix_orders_updated_at'), table_name='orders')
    op.drop_index(op.f('ix_orders_status'), table_name='orders')
    op.drop_index(op.f('ix_orders_product_name'), table_name='orders')
    op.drop_index(op.f('ix_orders_plan_no'), table_name='orders')
    op.drop_index(op.f('ix_orders_plan_date'), table_name='orders')
    op.drop_index(op.f('ix_orders_customer_id'), table_name='orders')
    op.drop_index(op.f('ix_orders_created_by'), table_name='orders')
    op.drop_index(op.f('ix_orders_created_at'), table_name='orders')
    op.drop_table('orders')
    op.drop_index(op.f('ix_activation_codes_user_id'), table_name='activation_codes')
    op.drop_index(op.f('ix_activation_codes_code'), table_name='activation_codes')
    op.drop_table('activation_codes')
    op.drop_index(op.f('ix_warehouses_name'), table_name='warehouses')
    op.drop_index(op.f('ix_warehouses_is_active'), table_name='warehouses')
    op.drop_table('warehouses')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_status'), table_name='users')
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_index(op.f('ix_users_customer_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_super_admin_credentials_username'), table_name='super_admin_credentials')
    op.drop_index(op.f('ix_super_admin_credentials_is_active'), table_name='super_admin_credentials')
    op.drop_table('super_admin_credentials')
    op.drop_index(op.f('ix_oil_products_name'), table_name='oil_products')
    op.drop_index(op.f('ix_oil_products_is_active'), table_name='oil_products')
    op.drop_table('oil_products')
    op.drop_index(op.f('ix_inventory_warehouse_id'), table_name='inventory')
    op.drop_index(op.f('ix_inventory_updated_at'), table_name='inventory')
    op.drop_index(op.f('ix_inventory_product_name'), table_name='inventory')
    op.drop_table('inventory')
    op.drop_index(op.f('ix_business_logs_user_id'), table_name='business_logs')
    op.drop_index(op.f('ix_business_logs_role'), table_name='business_logs')
    op.drop_index(op.f('ix_business_logs_result'), table_name='business_logs')
    op.drop_index(op.f('ix_business_logs_request_id'), table_name='business_logs')
    op.drop_index(op.f('ix_business_logs_order_id'), table_name='business_logs')
    op.drop_index(op.f('ix_business_logs_entity_type'), table_name='business_logs')
    op.drop_index(op.f('ix_business_logs_entity_id'), table_name='business_logs')
    op.drop_index(op.f('ix_business_logs_created_at'), table_name='business_logs')
    op.drop_index(op.f('ix_business_logs_action'), table_name='business_logs')
    op.drop_table('business_logs')
