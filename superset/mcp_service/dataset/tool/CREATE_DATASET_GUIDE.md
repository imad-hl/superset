# How to Add an MCP Tool: Complete Guide

**A Step-by-Step Tutorial on Adding the `create_dataset` Tool**

This guide explains how we added the `create_dataset` tool to the Superset MCP service. Follow this pattern to add your own MCP tools!

---

## 📚 Table of Contents

1. [What is an MCP Tool?](#what-is-an-mcp-tool)
2. [Understanding the Architecture](#understanding-the-architecture)
3. [Step-by-Step Implementation](#step-by-step-implementation)
4. [Testing Your Tool](#testing-your-tool)
5. [Common Pitfalls & Solutions](#common-pitfalls--solutions)
6. [Quick Checklist](#quick-checklist)

---

## What is an MCP Tool?

An **MCP (Model Context Protocol) tool** is a function that AI agents (like Claude) can call to perform actions in Superset. Think of it like an API endpoint, but specifically designed for AI agents.

For example:
- `list_datasets` - Lists all datasets
- `create_chart` - Creates a new chart
- `create_dataset` - Creates a new dataset (what we built!)

When an AI agent wants to create a dataset, it calls our `create_dataset` tool with parameters like database ID, table name, etc.

---

## Understanding the Architecture

Before we start, let's understand the key components:

```
superset/mcp_service/dataset/
├── schemas.py              # 📝 Request/Response data models
├── tool/
│   ├── __init__.py        # 📦 Exports all tools
│   ├── list_datasets.py   # 🔍 Existing tool example
│   └── create_dataset.py  # ✨ Our new tool!
└── tests/
    └── test_create_dataset.py  # 🧪 Unit tests
```

### Key Files to Touch:

1. **`schemas.py`** - Define what data your tool accepts and returns
2. **`tool/create_dataset.py`** - The actual tool implementation
3. **`tool/__init__.py`** - Register the tool for export
4. **`app.py`** - Import the tool so MCP knows about it
5. **`tests/test_create_dataset.py`** - Test your tool works correctly

---

## Step-by-Step Implementation

### Step 1: Define Your Schemas (Data Models)

**File:** `superset/mcp_service/dataset/schemas.py`

Schemas define what data your tool accepts (request) and what it returns (response). We use Pydantic for this.

```python
from pydantic import BaseModel, Field
from typing import Annotated

class CreateDatasetRequest(BaseModel):
    """What data does the tool need?"""
    
    database_id: Annotated[
        int,
        Field(description="ID of the database")
    ]
    table_name: Annotated[
        str,
        Field(description="Name of the table")
    ]
    schema_name: Annotated[
        str | None,
        Field(default=None, description="Schema name (required for physical tables)")
    ]
    # ... more fields

class CreateDatasetResponse(BaseModel):
    """What does the tool return?"""
    
    success: bool = Field(..., description="Did it work?")
    dataset: DatasetInfo | None = Field(None, description="The created dataset")
    message: str = Field(..., description="Success or error message")
    error: str | None = Field(None, description="Error details if failed")
```

**Why?**
- AI agents need to know what parameters to send
- Pydantic validates the data automatically
- Clear descriptions help AI understand how to use the tool

**Key Points:**
- Use `Annotated[type, Field(...)]` for all fields
- Add clear descriptions - AI reads these!
- Use `| None` for optional fields
- Add validation with `@model_validator` if needed

### Step 2: Implement the Tool

**File:** `superset/mcp_service/dataset/tool/create_dataset.py`

This is where the actual work happens. Every tool follows this pattern:

```python
import logging
from fastmcp import Context
from superset_core.mcp import tool

from superset.commands.dataset.create import CreateDatasetCommand
from superset.mcp_service.dataset.schemas import (
    CreateDatasetRequest,
    CreateDatasetResponse,
)
from superset.mcp_service.utils.schema_utils import parse_request

logger = logging.getLogger(__name__)

@tool(tags=["mutate"])  # 🏷️ Tag it (for filtering)
@parse_request(CreateDatasetRequest)  # 🔍 Parse & validate input
async def create_dataset(
    request: CreateDatasetRequest, 
    ctx: Context
) -> CreateDatasetResponse:
    """Create a new dataset in Superset.
    
    This docstring is important! AI agents read it to understand
    what the tool does and how to use it.
    
    Example:
    ```json
    {
        "database_id": 1,
        "table_name": "sales_data",
        "schema": "public"
    }
    ```
    """
    
    # 1. Log what we're doing (helpful for debugging)
    await ctx.info(f"Creating dataset: {request.table_name}")
    
    try:
        # 2. Build the command data
        command_data = {
            "database": request.database_id,
            "table_name": request.table_name,
        }
        
        if request.schema_name:
            command_data["schema"] = request.schema_name
        
        # 3. Execute the Superset command
        command = CreateDatasetCommand(command_data)
        dataset = command.run()
        
        # 4. Return success response
        return CreateDatasetResponse(
            success=True,
            dataset=serialize_dataset_object(dataset),
            message=f"Dataset '{request.table_name}' created successfully"
        )
        
    except Exception as e:
        # 5. Handle errors gracefully
        await ctx.error(f"Failed to create dataset: {str(e)}")
        return CreateDatasetResponse(
            success=False,
            message="Dataset creation failed",
            error=str(e)
        )
```

**Key Components Explained:**

1. **`@tool(tags=["mutate"])`** 
   - Registers this function as an MCP tool
   - `tags=["mutate"]` means it modifies data (vs. just reading)
   - AI agents can filter tools by tags

2. **`@parse_request(CreateDatasetRequest)`**
   - Automatically parses and validates input
   - Converts JSON from AI agent into Python object
   - Handles validation errors automatically

3. **`async def`**
   - MCP tools are asynchronous
   - Use `await ctx.info()` for logging
   - Use `await ctx.report_progress()` for long operations

4. **Context (`ctx`)**
   - `ctx.info()` - Log info messages
   - `ctx.error()` - Log errors
   - `ctx.debug()` - Log debug details
   - `ctx.report_progress(current, total, message)` - Show progress

5. **Superset Commands**
   - Use existing Superset commands (like `CreateDatasetCommand`)
   - Don't duplicate business logic
   - Commands handle validation, permissions, database operations

### Step 3: Register the Tool

**File:** `superset/mcp_service/dataset/tool/__init__.py`

Make your tool available by exporting it:

```python
from .create_dataset import create_dataset  # ← Add this
from .get_dataset_info import get_dataset_info
from .list_datasets import list_datasets

__all__ = [
    "create_dataset",  # ← Add this
    "list_datasets",
    "get_dataset_info",
]
```

**Why?**
- Python modules need explicit exports
- This makes `from superset.mcp_service.dataset.tool import create_dataset` work

### Step 4: Import in App

**File:** `superset/mcp_service/app.py`

Import your tool so the MCP service knows about it:

```python
from superset.mcp_service.dataset.tool import (
    create_dataset,  # ← Add this line
    get_dataset_available_filters,
    get_dataset_info,
    list_datasets,
)
```

**Also update the instructions string:**

```python
Dataset Management:
- list_datasets: List datasets with advanced filters
- get_dataset_info: Get detailed dataset information
- create_dataset: Create a new dataset (physical or SQL-based)  # ← Add this
- get_dataset_available_filters: List available filters
```

**Why?**
- The `@tool` decorator auto-registers on import
- If you don't import it, the tool won't be available
- Instructions help AI understand what tools exist

---

## Testing Your Tool

### Step 5: Write Unit Tests

**File:** `tests/unit_tests/mcp_service/dataset/tool/test_create_dataset.py`

Testing ensures your tool works correctly. Here's the pattern:

```python
import pytest
from unittest.mock import MagicMock, patch
from fastmcp import Client

from superset.mcp_service.app import mcp
from superset.mcp_service.dataset.schemas import CreateDatasetRequest

@pytest.fixture
def mcp_server():
    """Provide the MCP server for testing"""
    return mcp

@pytest.fixture(autouse=True)
def mock_auth():
    """Mock authentication so tests don't need real login"""
    with patch("superset.mcp_service.auth.get_user_from_request") as mock:
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "admin"
        mock.return_value = mock_user
        yield mock

@patch("superset.mcp_service.dataset.tool.create_dataset.CreateDatasetCommand")
@pytest.mark.asyncio
async def test_create_dataset_physical_table(mock_command_class, mcp_server):
    """Test creating a physical table dataset"""
    
    # 1. Create a mock dataset that will be "created"
    mock_dataset = MagicMock()
    mock_dataset.id = 1
    mock_dataset.table_name = "sales_data"
    mock_dataset.schema = "public"
    
    # 2. Mock the command to return our mock dataset
    mock_command = MagicMock()
    mock_command.run.return_value = mock_dataset
    mock_command_class.return_value = mock_command
    
    # 3. Call the tool
    async with Client(mcp_server) as client:
        request = CreateDatasetRequest(
            database_id=1,
            table_name="sales_data",
            schema="public",
        )
        
        result = await client.call_tool(
            "create_dataset", 
            {"request": request.model_dump()}
        )
        
        # 4. Check the response
        response_data = json.loads(result.content[0].text)
        assert response_data["success"] is True
        assert response_data["dataset"]["id"] == 1
        assert response_data["dataset"]["table_name"] == "sales_data"
```

**Test Categories:**

1. **Happy Path Tests** - Normal successful usage
2. **Error Tests** - What happens when things go wrong
3. **Validation Tests** - Test input validation
4. **Edge Cases** - Unusual but valid inputs

**Run Tests:**

```bash
# In Docker container
docker exec superset_dev_latest-superset-1 \
  pytest tests/unit_tests/mcp_service/dataset/tool/test_create_dataset.py -v

# Locally (if environment is set up)
pytest tests/unit_tests/mcp_service/dataset/tool/test_create_dataset.py -v
```

---

## Common Pitfalls & Solutions

### 1. **Pydantic Field Shadowing**

**Problem:** Field name conflicts with BaseModel methods

```python
# ❌ BAD - "schema" shadows BaseModel.schema()
class MyRequest(BaseModel):
    schema: str
```

**Solution:** Use field alias

```python
# ✅ GOOD - Use schema_name with alias
class MyRequest(BaseModel):
    schema_name: str = Field(alias="schema")
    
    model_config = ConfigDict(populate_by_name=True)
```

### 2. **Forgot to Import Tool**

**Problem:** Tool doesn't appear in MCP

**Solution:** Check these locations:
1. `tool/__init__.py` - Export added?
2. `app.py` - Import added?
3. Restart MCP service

### 3. **Async/Await Confusion**

**Problem:** `RuntimeWarning: coroutine was never awaited`

```python
# ❌ BAD
ctx.info("message")  # Missing await!
```

**Solution:** Always await context methods

```python
# ✅ GOOD
await ctx.info("message")
```

### 4. **Schema Serialization Errors**

**Problem:** `PydanticSerializationError: Unable to serialize unknown type`

**Solution:** Make sure all response fields are serializable:
- Use basic types (str, int, bool, list, dict)
- Use Pydantic models for complex objects
- Avoid functions, classes, or special objects

### 5. **Missing Validation**

**Problem:** Bad data gets through, causes errors later

**Solution:** Add validators

```python
class CreateDatasetRequest(BaseModel):
    sql: str | None = None
    schema_name: str | None = None
    
    @model_validator(mode="after")
    def validate_sql_or_schema(self) -> "CreateDatasetRequest":
        if not self.sql and not self.schema_name:
            raise ValueError("Need either 'sql' or 'schema_name'")
        return self
```

---

## Quick Checklist

When adding a new MCP tool, check off these items:

### Implementation
- [ ] Create request schema in `schemas.py`
- [ ] Create response schema in `schemas.py`
- [ ] Implement tool in `tool/your_tool.py`
- [ ] Add `@tool()` decorator
- [ ] Add `@parse_request()` decorator
- [ ] Write comprehensive docstring
- [ ] Add error handling with try/except
- [ ] Use `await ctx.info()` for logging

### Registration
- [ ] Export tool in `tool/__init__.py`
- [ ] Import tool in `app.py`
- [ ] Update instructions string in `app.py`
- [ ] Update UPDATING.md if needed

### Testing
- [ ] Create test file `test_your_tool.py`
- [ ] Write happy path test
- [ ] Write error handling tests
- [ ] Write validation tests
- [ ] All tests pass locally
- [ ] All tests pass in Docker

### Documentation
- [ ] Docstring explains what tool does
- [ ] Docstring includes example usage
- [ ] Field descriptions are clear
- [ ] Edge cases documented in code comments

---

## Example: Minimal MCP Tool

Here's the absolute minimum for a working MCP tool:

**schemas.py:**
```python
from pydantic import BaseModel, Field

class HelloRequest(BaseModel):
    name: str = Field(description="Name to greet")

class HelloResponse(BaseModel):
    message: str = Field(description="Greeting message")
```

**tool/hello.py:**
```python
from superset_core.mcp import tool
from superset.mcp_service.utils.schema_utils import parse_request
from .schemas import HelloRequest, HelloResponse

@tool()
@parse_request(HelloRequest)
async def say_hello(request: HelloRequest, ctx) -> HelloResponse:
    """Say hello to someone."""
    await ctx.info(f"Saying hello to {request.name}")
    return HelloResponse(message=f"Hello, {request.name}!")
```

**tool/__init__.py:**
```python
from .hello import say_hello

__all__ = ["say_hello"]
```

**app.py:**
```python
from superset.mcp_service.tool import say_hello  # noqa: F401
```

Done! Your AI agent can now call `say_hello`.

---

## Advanced Topics

### Progress Reporting

For long-running operations:

```python
await ctx.report_progress(1, 5, "Validating input")
# ... do validation ...
await ctx.report_progress(2, 5, "Creating dataset")
# ... create dataset ...
await ctx.report_progress(5, 5, "Done!")
```

### Conditional Logic

Handle different scenarios:

```python
if request.sql:
    # Virtual dataset
    await ctx.debug("Creating virtual dataset with SQL")
    command_data["sql"] = request.sql
else:
    # Physical dataset
    await ctx.debug("Creating physical table dataset")
    command_data["schema"] = request.schema_name
```

### Reusing Existing Code

Always use Superset's existing commands and DAOs:

```python
# ✅ GOOD - Use existing command
from superset.commands.dataset.create import CreateDatasetCommand
dataset = CreateDatasetCommand(data).run()

# ❌ BAD - Don't duplicate logic
dataset = Dataset()
dataset.table_name = table_name
db.session.add(dataset)
db.session.commit()
```

---

## Resources

- **MCP Specification:** https://modelcontextprotocol.io/
- **FastMCP Documentation:** https://github.com/jlowin/fastmcp
- **Pydantic Documentation:** https://docs.pydantic.dev/
- **Superset MCP Architecture:** `superset/mcp_service/ARCHITECTURE.md`
- **Superset MCP Guide for Claude:** `superset/mcp_service/CLAUDE.md`

---

## Summary

Adding an MCP tool involves:

1. **Define schemas** (request/response) in `schemas.py`
2. **Implement tool** with `@tool` decorator in `tool/your_tool.py`
3. **Register tool** in `__init__.py` and `app.py`
4. **Write tests** to ensure it works
5. **Document** with clear docstrings

Follow this pattern, and you can add any tool you need! The key is:
- Clear schemas with good descriptions
- Use existing Superset commands
- Handle errors gracefully
- Test thoroughly

Good luck building your MCP tools! 🚀
