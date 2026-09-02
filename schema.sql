CREATE TABLE addresses (
    "id" INTEGER,
    "customer_id" INTEGER,
    "address_type" VARCHAR,
    "postal_code" VARCHAR,
    "street" VARCHAR,
    "number" INTEGER,
    "complement" VARCHAR,
    "district" VARCHAR,
    "city" VARCHAR,
    "state" VARCHAR,
    "country" VARCHAR,
    "is_primary" VARCHAR
);

CREATE TABLE attributes (
    "id" INTEGER,
    "name" VARCHAR,
    "data_type" VARCHAR
);

CREATE TABLE brands (
    "id" INTEGER,
    "name" VARCHAR,
    "country" VARCHAR,
    "is_active" VARCHAR,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE categories (
    "id" INTEGER,
    "name" VARCHAR,
    "slug" VARCHAR,
    "parent_category_id" INTEGER,
    "is_active" VARCHAR,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE customers (
    "id" INTEGER,
    "person_type" VARCHAR,
    "legal_name" VARCHAR,
    "trade_name" VARCHAR,
    "tax_id" INTEGER,
    "state_registration" VARCHAR,
    "email" VARCHAR,
    "phone" INTEGER,
    "is_active" VARCHAR,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE employees (
    "id" INTEGER,
    "full_name" VARCHAR,
    "cpf" INTEGER,
    "email" VARCHAR,
    "role" VARCHAR,
    "primary_location_id" INTEGER,
    "hire_date" TIMESTAMP,
    "termination_date" TIMESTAMP,
    "is_active" VARCHAR,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE fiscal_invoices (
    "id" INTEGER,
    "order_id" INTEGER,
    "nfe_number" VARCHAR,
    "nfe_access_key" INTEGER,
    "series" INTEGER,
    "issued_at" TIMESTAMP,
    "status" VARCHAR,
    "total_amount" NUMERIC,
    "xml_storage_uri" VARCHAR,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE goods_receipt_items (
    "id" INTEGER,
    "goods_receipt_id" INTEGER,
    "purchase_order_item_id" INTEGER,
    "quantity_received" NUMERIC
);

CREATE TABLE goods_receipts (
    "id" INTEGER,
    "purchase_order_id" INTEGER,
    "received_by_employee_id" INTEGER,
    "received_at" TIMESTAMP,
    "notes" VARCHAR,
    "created_at" TIMESTAMP
);

CREATE TABLE locations (
    "id" INTEGER,
    "name" VARCHAR,
    "location_type" VARCHAR,
    "postal_code" VARCHAR,
    "street" VARCHAR,
    "number" INTEGER,
    "complement" VARCHAR,
    "district" VARCHAR,
    "city" VARCHAR,
    "state" VARCHAR,
    "country" VARCHAR,
    "is_active" VARCHAR,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE order_items (
    "id" INTEGER,
    "order_id" INTEGER,
    "product_variant_id" INTEGER,
    "quantity" INTEGER,
    "unit_price" NUMERIC,
    "icms_rate" NUMERIC,
    "ipi_rate" NUMERIC,
    "line_total" NUMERIC
);

CREATE TABLE orders (
    "id" INTEGER,
    "order_number" VARCHAR,
    "channel" VARCHAR,
    "customer_id" INTEGER,
    "salesperson_id" INTEGER,
    "location_id" INTEGER,
    "status" VARCHAR,
    "subtotal" NUMERIC,
    "discount_amount" NUMERIC,
    "total" NUMERIC,
    "placed_at" TIMESTAMP,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE payments (
    "id" INTEGER,
    "order_id" INTEGER,
    "method" VARCHAR,
    "installments" INTEGER,
    "amount" NUMERIC,
    "status" VARCHAR,
    "paid_at" TIMESTAMP,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE product_suppliers (
    "product_variant_id" INTEGER,
    "supplier_id" INTEGER,
    "supplier_sku" VARCHAR,
    "last_quoted_cost" NUMERIC,
    "lead_time_days" INTEGER,
    "is_preferred" VARCHAR,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE product_variants (
    "id" INTEGER,
    "product_id" INTEGER,
    "sku" VARCHAR,
    "barcode_ean" INTEGER,
    "sale_price" NUMERIC,
    "cost_price" NUMERIC,
    "weight_kg" NUMERIC,
    "icms_rate" NUMERIC,
    "ipi_rate" NUMERIC,
    "is_active" VARCHAR,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE products (
    "id" INTEGER,
    "name" VARCHAR,
    "description" VARCHAR,
    "brand_id" INTEGER,
    "category_id" INTEGER,
    "ncm_code" INTEGER,
    "unit_of_measure" VARCHAR,
    "is_active" VARCHAR,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE purchase_order_items (
    "id" INTEGER,
    "purchase_order_id" INTEGER,
    "product_variant_id" INTEGER,
    "quantity_ordered" INTEGER,
    "unit_cost" NUMERIC,
    "line_total" NUMERIC
);

CREATE TABLE purchase_orders (
    "id" INTEGER,
    "po_number" VARCHAR,
    "supplier_id" INTEGER,
    "buyer_id" INTEGER,
    "destination_location_id" INTEGER,
    "status" VARCHAR,
    "currency" VARCHAR,
    "subtotal" NUMERIC,
    "total" NUMERIC,
    "placed_at" TIMESTAMP,
    "expected_delivery_at" TIMESTAMP,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE return_items (
    "id" INTEGER,
    "return_id" INTEGER,
    "order_item_id" INTEGER,
    "quantity" NUMERIC,
    "action" VARCHAR,
    "exchange_variant_id" INTEGER,
    "unit_refund_amount" NUMERIC
);

CREATE TABLE returns (
    "id" INTEGER,
    "return_number" VARCHAR,
    "order_id" INTEGER,
    "customer_id" INTEGER,
    "received_at_location_id" INTEGER,
    "status" VARCHAR,
    "reason" VARCHAR,
    "total_refund_amount" NUMERIC,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE stock_levels (
    "product_variant_id" INTEGER,
    "location_id" INTEGER,
    "quantity_on_hand" NUMERIC,
    "reorder_point" VARCHAR,
    "updated_at" TIMESTAMP
);

CREATE TABLE stock_movements (
    "id" INTEGER,
    "product_variant_id" INTEGER,
    "location_id" INTEGER,
    "movement_type" VARCHAR,
    "quantity" NUMERIC,
    "reference_table" VARCHAR,
    "reference_id" VARCHAR,
    "employee_id" VARCHAR,
    "notes" VARCHAR,
    "occurred_at" TIMESTAMP,
    "created_at" TIMESTAMP
);

CREATE TABLE suppliers (
    "id" INTEGER,
    "legal_name" VARCHAR,
    "trade_name" VARCHAR,
    "country" VARCHAR,
    "tax_id" VARCHAR,
    "tax_id_type" VARCHAR,
    "email" VARCHAR,
    "phone" INTEGER,
    "contact_name" VARCHAR,
    "is_active" VARCHAR,
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP
);

CREATE TABLE variant_attribute_values (
    "product_variant_id" INTEGER,
    "attribute_id" INTEGER,
    "value" VARCHAR
);
