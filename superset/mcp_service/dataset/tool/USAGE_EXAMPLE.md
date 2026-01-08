# Create Dataset Tool - Usage Examples

## Overview
The `create_dataset` tool allows you to create datasets in Superset using either database ID or database name, making it much more user-friendly.

## Quick Start

### Option 1: Using Database Name (Recommended)
```json
{
  "database_name": "PostgreSQL Production",
  "table_name": "users",
  "schema": "public"
}
```

### Option 2: Using Database ID (Legacy)
```json
{
  "database_id": 123,
  "table_name": "users",
  "schema": "public"
}
```

## Physical Table Examples

### Basic Physical Table
```json
{
  "database_name": "Analytics DB",
  "table_name": "sales_transactions",
  "schema": "public"
}
```

### Physical Table with Metadata Fetch
```json
{
  "database_name": "MySQL Production",
  "table_name": "customers",
  "schema": "customer_data",
  "fetch_metadata": true
}
```

### Physical Table with Catalog (Trino/Presto)
```json
{
  "database_name": "Trino Cluster",
  "catalog": "hive",
  "schema": "default",
  "table_name": "events"
}
```

## Virtual Dataset Examples

### Basic SQL Query
```json
{
  "database_name": "BigQuery Analytics",
  "table_name": "customer_360",
  "sql": "SELECT * FROM customers LEFT JOIN orders USING (customer_id)"
}
```

### Complex SQL with Multiple Tables
```json
{
  "database_name": "Snowflake Warehouse",
  "table_name": "revenue_summary",
  "sql": "SELECT date, product_id, SUM(amount) as revenue FROM sales GROUP BY date, product_id"
}
```

## Advanced Features

### With Owners
```json
{
  "database_name": "PostgreSQL",
  "table_name": "products",
  "schema": "inventory",
  "owners": [42, 108]
}
```

### Without Metadata Fetch (Faster)
```json
{
  "database_name": "ClickHouse",
  "table_name": "logs",
  "schema": "system",
  "fetch_metadata": false
}
```

## How Database Name Resolution Works

1. You provide `database_name` (e.g., "PostgreSQL Production")
2. The tool looks up the database by name using `DatabaseDAO.get_database_by_name()`
3. It automatically resolves to the internal database ID
4. The dataset is created with the resolved ID

### Benefits
- **Intuitive**: Use the database name you see in the UI
- **No ID lookup**: No need to find the database ID manually
- **Error handling**: Clear error message if database name doesn't exist
- **Backward compatible**: Still works with `database_id` if you prefer

## Error Handling

### Database Not Found
```json
{
  "database_name": "NonExistentDB",
  "table_name": "users"
}
```
**Error**: `Database with name 'NonExistentDB' not found`

### Missing Database Identifier
```json
{
  "table_name": "users",
  "schema": "public"
}
```
**Error**: `Either 'database_id' or 'database_name' must be provided`

### Both Database Identifiers Provided
```json
{
  "database_id": 123,
  "database_name": "PostgreSQL",
  "table_name": "users"
}
```
**Error**: `Cannot provide both 'database_id' and 'database_name'. Use only one.`

### Missing Schema for Physical Table
```json
{
  "database_name": "PostgreSQL",
  "table_name": "users"
}
```
**Error**: `'schema' is required for physical table datasets`

## Tips

1. **Use database_name**: It's much easier than looking up IDs
2. **Include schema**: Always specify the schema for physical tables
3. **Fetch metadata**: Set `fetch_metadata: true` for new tables to auto-discover columns
4. **Virtual datasets**: Include the `sql` field to create query-based datasets
5. **Catalogs**: Use the `catalog` field for Trino/Presto three-level namespace

## Testing Your Setup

Try creating a simple dataset:
```json
{
  "database_name": "examples",
  "table_name": "birth_names",
  "schema": "main"
}
```

If your Superset instance has the example data loaded, this should work immediately!
