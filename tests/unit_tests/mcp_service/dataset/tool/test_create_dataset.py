# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""Tests for create_dataset MCP tool."""

import logging
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastmcp import Client
from marshmallow import ValidationError

from superset.commands.dataset.exceptions import (
    DatasetCreateFailedError,
    DatasetInvalidError,
)
from superset.mcp_service.app import mcp
from superset.mcp_service.dataset.schemas import CreateDatasetRequest
from superset.utils import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture
def mcp_server():
    return mcp


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock authentication for all tests."""
    from unittest.mock import Mock, patch

    with patch("superset.mcp_service.auth.get_user_from_request") as mock_get_user:
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "admin"
        mock_get_user.return_value = mock_user
        yield mock_get_user


def create_mock_dataset(
    dataset_id=1,
    table_name="test_table",
    schema="public",
    database_id=1,
    is_virtual=False,
    sql=None,
):
    """Create a mock dataset object for testing."""
    dataset = MagicMock()
    dataset.id = dataset_id
    dataset.table_name = table_name
    dataset.schema = schema
    dataset.database_id = database_id
    dataset.is_virtual = is_virtual
    dataset.sql = sql
    dataset.uuid = f"test-uuid-{dataset_id}"
    dataset.description = "Test dataset"
    dataset.changed_by_name = "admin"
    dataset.changed_on = None
    dataset.changed_on_humanized = None
    dataset.created_by_name = "admin"
    dataset.created_on = None
    dataset.created_on_humanized = None
    dataset.tags = []
    dataset.owners = []
    dataset.database = MagicMock()
    dataset.database.database_name = "test_db"
    dataset.schema_perm = f"[test_db].[{schema}]"
    dataset.url = f"/tablemodelview/edit/{dataset_id}"
    dataset.main_dttm_col = None
    dataset.offset = 0
    dataset.cache_timeout = 0
    dataset.params = {}
    dataset.template_params = {}
    dataset.extra = {}
    dataset.columns = []
    dataset.metrics = []
    dataset.is_favorite = False
    dataset.fetch_metadata = MagicMock()
    return dataset


@patch("superset.mcp_service.dataset.tool.create_dataset.CreateDatasetCommand")
@pytest.mark.asyncio
async def test_create_dataset_physical_table(mock_command_class, mcp_server):
    """Test creating a physical table-based dataset."""
    # Create mock dataset
    mock_dataset = create_mock_dataset(
        dataset_id=1,
        table_name="sales_data",
        schema="public",
        database_id=1,
        is_virtual=False,
    )

    # Mock the command
    mock_command = MagicMock()
    mock_command.run.return_value = mock_dataset
    mock_command_class.return_value = mock_command

    async with Client(mcp_server) as client:
        request = CreateDatasetRequest(
            database_id=1,
            table_name="sales_data",
            schema="public",
            description="Sales data table",
        )

        result = await client.call_tool(
            "create_dataset", {"request": request.model_dump()}
        )

        # Parse response
        response_data = json.loads(result.content[0].text)

        # Assertions
        assert response_data["success"] is True
        assert response_data["dataset"]["id"] == 1
        assert response_data["dataset"]["table_name"] == "sales_data"
        assert response_data["dataset"]["schema"] == "public"
        assert response_data["dataset"]["is_virtual"] is False
        assert "sales_data" in response_data["message"].lower()
        assert "created successfully" in response_data["message"].lower()

        # Verify command was called correctly
        mock_command_class.assert_called_once()
        call_args = mock_command_class.call_args[0][0]
        assert call_args["database"] == 1
        assert call_args["table_name"] == "sales_data"
        assert call_args["schema"] == "public"
        assert call_args["description"] == "Sales data table"
        assert "sql" not in call_args


@patch("superset.mcp_service.dataset.tool.create_dataset.CreateDatasetCommand")
@pytest.mark.asyncio
async def test_create_dataset_virtual_sql(mock_command_class, mcp_server):
    """Test creating a virtual SQL-based dataset."""
    sql_query = "SELECT product_name, SUM(revenue) as total FROM sales GROUP BY product_name"

    # Create mock virtual dataset
    mock_dataset = create_mock_dataset(
        dataset_id=2,
        table_name="Top Products",
        schema="public",
        database_id=1,
        is_virtual=True,
        sql=sql_query,
    )

    # Mock the command
    mock_command = MagicMock()
    mock_command.run.return_value = mock_dataset
    mock_command_class.return_value = mock_command

    async with Client(mcp_server) as client:
        request = CreateDatasetRequest(
            database_id=1,
            table_name="Top Products",
            sql=sql_query,
            description="Top selling products",
        )

        result = await client.call_tool(
            "create_dataset", {"request": request.model_dump()}
        )

        # Parse response
        response_data = json.loads(result.content[0].text)

        # Assertions
        assert response_data["success"] is True
        assert response_data["dataset"]["id"] == 2
        assert response_data["dataset"]["table_name"] == "Top Products"
        assert response_data["dataset"]["is_virtual"] is True
        assert response_data["dataset"]["sql"] == sql_query

        # Verify command was called with SQL
        call_args = mock_command_class.call_args[0][0]
        assert call_args["sql"] == sql_query


@patch("superset.mcp_service.dataset.tool.create_dataset.CreateDatasetCommand")
@pytest.mark.asyncio
async def test_create_dataset_with_metadata_fetch(mock_command_class, mcp_server):
    """Test creating dataset with automatic metadata fetching."""
    mock_dataset = create_mock_dataset()

    mock_command = MagicMock()
    mock_command.run.return_value = mock_dataset
    mock_command_class.return_value = mock_command

    async with Client(mcp_server) as client:
        request = CreateDatasetRequest(
            database_id=1,
            table_name="test_table",
            schema="public",
            fetch_metadata=True,
        )

        result = await client.call_tool(
            "create_dataset", {"request": request.model_dump()}
        )

        # Parse response
        response_data = json.loads(result.content[0].text)
        assert response_data["success"] is True

        # Verify fetch_metadata was called
        mock_dataset.fetch_metadata.assert_called_once()


@patch("superset.mcp_service.dataset.tool.create_dataset.CreateDatasetCommand")
@pytest.mark.asyncio
async def test_create_dataset_without_metadata_fetch(mock_command_class, mcp_server):
    """Test creating dataset without metadata fetching."""
    mock_dataset = create_mock_dataset()

    mock_command = MagicMock()
    mock_command.run.return_value = mock_dataset
    mock_command_class.return_value = mock_command

    async with Client(mcp_server) as client:
        request = CreateDatasetRequest(
            database_id=1,
            table_name="test_table",
            schema="public",
            fetch_metadata=False,
        )

        result = await client.call_tool(
            "create_dataset", {"request": request.model_dump()}
        )

        # Parse response
        response_data = json.loads(result.content[0].text)
        assert response_data["success"] is True

        # Verify fetch_metadata was NOT called
        mock_dataset.fetch_metadata.assert_not_called()


@patch("superset.mcp_service.dataset.tool.create_dataset.CreateDatasetCommand")
@pytest.mark.asyncio
async def test_create_dataset_with_owners(mock_command_class, mcp_server):
    """Test creating dataset with specified owners."""
    mock_dataset = create_mock_dataset()

    mock_command = MagicMock()
    mock_command.run.return_value = mock_dataset
    mock_command_class.return_value = mock_command

    async with Client(mcp_server) as client:
        request = CreateDatasetRequest(
            database_id=1,
            table_name="test_table",
            schema="public",
            owner_ids=[1, 2, 3],
        )

        result = await client.call_tool(
            "create_dataset", {"request": request.model_dump()}
        )

        # Parse response
        response_data = json.loads(result.content[0].text)
        assert response_data["success"] is True

        # Verify owners were passed to command
        call_args = mock_command_class.call_args[0][0]
        assert call_args["owners"] == [1, 2, 3]


@patch("superset.mcp_service.dataset.tool.create_dataset.CreateDatasetCommand")
@pytest.mark.asyncio
async def test_create_dataset_validation_error(mock_command_class, mcp_server):
    """Test dataset creation with validation errors."""
    # Create validation error
    validation_error = ValidationError("Table already exists", field_name="table_name")
    invalid_error = DatasetInvalidError(exceptions=[validation_error])

    # Mock the command to raise validation error
    mock_command = MagicMock()
    mock_command.run.side_effect = invalid_error
    mock_command_class.return_value = mock_command

    async with Client(mcp_server) as client:
        request = CreateDatasetRequest(
            database_id=1,
            table_name="duplicate_table",
            schema="public",
        )

        result = await client.call_tool(
            "create_dataset", {"request": request.model_dump()}
        )

        # Parse response
        response_data = json.loads(result.content[0].text)

        # Assertions
        assert response_data["success"] is False
        assert "validation" in response_data["message"].lower()
        assert len(response_data["validation_errors"]) > 0


@patch("superset.mcp_service.dataset.tool.create_dataset.CreateDatasetCommand")
@pytest.mark.asyncio
async def test_create_dataset_create_failed_error(mock_command_class, mcp_server):
    """Test dataset creation failure."""
    # Mock the command to raise creation error
    mock_command = MagicMock()
    mock_command.run.side_effect = DatasetCreateFailedError("Database connection failed")
    mock_command_class.return_value = mock_command

    async with Client(mcp_server) as client:
        request = CreateDatasetRequest(
            database_id=999,  # Non-existent database
            table_name="test_table",
            schema="public",
        )

        result = await client.call_tool(
            "create_dataset", {"request": request.model_dump()}
        )

        # Parse response
        response_data = json.loads(result.content[0].text)

        # Assertions
        assert response_data["success"] is False
        assert "failed" in response_data["message"].lower()
        assert response_data["error"] is not None


@pytest.mark.asyncio
async def test_create_dataset_missing_schema_for_physical(mcp_server):
    """Test validation error when schema is missing for physical table."""
    # This should fail validation because physical tables need schema
    with pytest.raises(ValueError) as exc_info:
        request = CreateDatasetRequest(
            database_id=1,
            table_name="test_table",
            # schema is missing and sql is not provided
        )

    # Verify validation error message
    assert "schema" in str(exc_info.value).lower() or "required" in str(
        exc_info.value
    ).lower()


@patch("superset.mcp_service.dataset.tool.create_dataset.CreateDatasetCommand")
@pytest.mark.asyncio
async def test_create_dataset_with_catalog(mock_command_class, mcp_server):
    """Test creating dataset with catalog specified."""
    mock_dataset = create_mock_dataset()

    mock_command = MagicMock()
    mock_command.run.return_value = mock_dataset
    mock_command_class.return_value = mock_command

    async with Client(mcp_server) as client:
        request = CreateDatasetRequest(
            database_id=1,
            table_name="test_table",
            schema="public",
            catalog="my_catalog",
        )

        result = await client.call_tool(
            "create_dataset", {"request": request.model_dump()}
        )

        # Parse response
        response_data = json.loads(result.content[0].text)
        assert response_data["success"] is True

        # Verify catalog was passed to command
        call_args = mock_command_class.call_args[0][0]
        assert call_args["catalog"] == "my_catalog"


@patch("superset.mcp_service.dataset.tool.create_dataset.CreateDatasetCommand")
@pytest.mark.asyncio
async def test_create_dataset_metadata_fetch_failure(mock_command_class, mcp_server):
    """Test that metadata fetch failures don't break dataset creation."""
    mock_dataset = create_mock_dataset()
    # Make fetch_metadata raise an exception
    mock_dataset.fetch_metadata.side_effect = Exception("Metadata fetch failed")

    mock_command = MagicMock()
    mock_command.run.return_value = mock_dataset
    mock_command_class.return_value = mock_command

    async with Client(mcp_server) as client:
        request = CreateDatasetRequest(
            database_id=1,
            table_name="test_table",
            schema="public",
            fetch_metadata=True,
        )

        result = await client.call_tool(
            "create_dataset", {"request": request.model_dump()}
        )

        # Parse response - should still succeed despite metadata failure
        response_data = json.loads(result.content[0].text)
        assert response_data["success"] is True
        assert response_data["dataset"]["id"] == 1


@patch("superset.daos.database.DatabaseDAO.get_database_by_name")
@patch("superset.mcp_service.dataset.tool.create_dataset.CreateDatasetCommand")
@pytest.mark.asyncio
async def test_create_dataset_with_database_name(
    mock_command_class, mock_get_db_by_name, mcp_server
):
    """Test creating dataset using database_name instead of database_id."""
    # Mock database lookup
    mock_database = MagicMock()
    mock_database.id = 5
    mock_database.database_name = "PostgreSQL Production"
    mock_get_db_by_name.return_value = mock_database

    # Mock dataset creation
    mock_dataset = create_mock_dataset(dataset_id=10, database_id=5)
    mock_command = MagicMock()
    mock_command.run.return_value = mock_dataset
    mock_command_class.return_value = mock_command

    async with Client(mcp_server) as client:
        request = CreateDatasetRequest(
            database_name="PostgreSQL Production",
            table_name="sales_data",
            schema="public",
        )

        result = await client.call_tool(
            "create_dataset", {"request": request.model_dump()}
        )

        # Parse response
        response_data = json.loads(result.content[0].text)
        assert response_data["success"] is True
        assert response_data["dataset"]["id"] == 10

        # Verify database was looked up by name
        mock_get_db_by_name.assert_called_once_with("PostgreSQL Production")

        # Verify command was called with resolved database_id
        call_args = mock_command_class.call_args[0][0]
        assert call_args["database"] == 5


@patch("superset.daos.database.DatabaseDAO.get_database_by_name")
@pytest.mark.asyncio
async def test_create_dataset_database_name_not_found(
    mock_get_db_by_name, mcp_server
):
    """Test error when database_name doesn't exist."""
    # Mock database not found
    mock_get_db_by_name.return_value = None

    async with Client(mcp_server) as client:
        request = CreateDatasetRequest(
            database_name="NonExistent DB",
            table_name="test_table",
            schema="public",
        )

        result = await client.call_tool(
            "create_dataset", {"request": request.model_dump()}
        )

        # Parse response
        response_data = json.loads(result.content[0].text)
        assert response_data["success"] is False
        assert "NonExistent DB" in response_data["message"]
        assert "not found" in response_data["message"].lower()


@pytest.mark.asyncio
async def test_create_dataset_missing_both_database_identifiers(mcp_server):
    """Test validation error when neither database_id nor database_name provided."""
    with pytest.raises(ValueError) as exc_info:
        CreateDatasetRequest(
            # Neither database_id nor database_name provided
            table_name="test_table",
            schema="public",
        )

    assert "database_id" in str(exc_info.value).lower() or "database_name" in str(
        exc_info.value
    ).lower()


@pytest.mark.asyncio
async def test_create_dataset_both_database_identifiers(mcp_server):
    """Test validation error when both database_id and database_name provided."""
    with pytest.raises(ValueError) as exc_info:
        CreateDatasetRequest(
            database_id=1,
            database_name="PostgreSQL",  # Can't provide both!
            table_name="test_table",
            schema="public",
        )

    assert "both" in str(exc_info.value).lower()
