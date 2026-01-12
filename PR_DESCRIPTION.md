## feat(mcp): add create_dataset and list_databases MCP tools

### SUMMARY

This PR adds two new MCP (Model Context Protocol) tools to enhance Superset's AI agent capabilities:

1. **`create_dataset`** - Create new datasets (physical tables or virtual SQL-based datasets)
2. **`list_databases`** - List all available database connections in Superset

#### Why These Tools Are Needed

**Problem**: Users working with MCP agents couldn't:
- Create new datasets programmatically
- Discover which databases are available in their Superset instance
- Know what database names to use when creating datasets

**Solution**: These tools provide essential CRUD operations for datasets and discovery capabilities for database connections.

#### Key Features

**create_dataset tool:**
- Supports both physical tables and virtual SQL datasets
- Accepts `database_id` OR `database_name` for better UX
- Automatic column metadata fetching
- Owner assignment support
- Comprehensive validation with clear error messages

**list_databases tool:**
- Lists all database connections (bypasses RBAC for admin context)
- Returns database metadata: ID, name, backend type, permissions
- Essential for discovering correct database names before creating datasets

### TESTING INSTRUCTIONS

#### 1. Setup MCP Service
```bash
# Start the MCP service
superset mcp run --host 0.0.0.0
```

#### 2. Test list_databases Tool
Call the tool with an empty request:
```json
{}
```

Expected response:
```json
{
  "success": true,
  "count": 2,
  "databases": [
    {
      "id": 1,
      "name": "examples",
      "backend": "duckdb",
      "allow_dml": true,
      "expose_in_sqllab": true
    },
    {
      "id": 2,
      "name": "PostgreSQL Production",
      "backend": "postgresql",
      "allow_dml": true,
      "expose_in_sqllab": true
    }
  ]
}
```

#### 3. Test create_dataset Tool

**Test Case 1: Physical Table**
```json
{
  "database_name": "examples",
  "table_name": "birth_names",
  "schema": "main"
}
```

**Test Case 2: Virtual Dataset**
```json
{
  "database_name": "examples",
  "sql": "SELECT name, COUNT(*) as count FROM birth_names GROUP BY name LIMIT 10"
}
```

**Test Case 3: With Owners**
```json
{
  "database_id": 1,
  "table_name": "birth_names",
  "schema": "main",
  "owners": [1]
}
```

Expected: All should return success with dataset metadata including columns and metrics.

#### 4. Run Unit Tests
```bash
pytest tests/unit_tests/mcp_service/dataset/tool/test_create_dataset.py -v
pytest tests/unit_tests/mcp_service/database/tool/test_list_databases.py -v
```

Expected: All tests pass (14 tests for create_dataset).

### ADDITIONAL INFORMATION

- [x] Has associated issue: (none - new feature)
- [ ] Required feature flags: None
- [ ] Changes UI: No
- [ ] Includes DB Migration: No
- [x] Introduces new feature or API
- [ ] Removes existing feature or API

#### Implementation Details

**New Module Structure:**
```
superset/mcp_service/
├── database/                  # NEW: Database connection operations
│   ├── __init__.py
│   ├── schemas.py            # ListDatabasesRequest/Response, DatabaseInfo
│   └── tool/
│       ├── __init__.py
│       └── list_databases.py
├── dataset/
│   ├── schemas.py            # MODIFIED: Added CreateDatasetRequest/Response
│   └── tool/
│       ├── __init__.py       # MODIFIED: Exports create_dataset
│       ├── create_dataset.py # NEW
│       ├── CREATE_DATASET_GUIDE.md  # NEW: Developer guide
│       └── USAGE_EXAMPLE.md  # NEW: Usage examples
├── app.py                    # MODIFIED: Registered new tools
└── IMPLEMENTATION_GUIDE.md   # NEW: Comprehensive documentation
```

**Files Changed:**
- Modified: 3 files (app.py, dataset/schemas.py, dataset/tool/__init__.py)
- Added: 11 files (new module + tools + tests + docs)

**Test Coverage:**
- 14 unit tests for create_dataset (100% pass rate)
- 3 unit tests for list_databases

#### Technical Highlights

1. **Database Name Resolution**: Accepts both `database_id` and `database_name`, resolving names to IDs via `DatabaseDAO.get_database_by_name()`

2. **Pydantic Validation**: Uses `model_validator` for complex validation rules (e.g., ensuring exactly one database identifier is provided)

3. **SQLAlchemy Session Management**: Properly handles database object attribute access to avoid `DetachedInstanceError`

4. **RBAC Context**: `list_databases` uses `skip_base_filter=True` since MCP tools run with admin context

5. **FastMCP Integration**: Follows existing patterns with `@tool()` and `@parse_request()` decorators

#### Documentation Provided

- **IMPLEMENTATION_GUIDE.md**: Comprehensive guide covering implementation, challenges, solutions, and best practices
- **CREATE_DATASET_GUIDE.md**: Step-by-step tutorial for developers
- **USAGE_EXAMPLE.md**: Quick reference with examples

#### Breaking Changes

None. This is a purely additive feature.

---

### Checklist
- [x] Code follows project conventions
- [x] Tests added and passing
- [x] Documentation provided
- [x] Apache license headers added to all new files
- [x] No breaking changes
- [x] Works with existing MCP service infrastructure
