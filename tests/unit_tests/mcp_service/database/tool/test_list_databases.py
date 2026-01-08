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

"""Tests for list_databases MCP tool."""

import pytest
from unittest.mock import MagicMock, Mock, patch

from superset.mcp_service.database.schemas import ListDatabasesRequest
from superset.mcp_service.database.tool.list_databases import list_databases


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock authentication for all tests."""
    with patch("superset.mcp_service.auth.get_user_from_request") as mock_get_user:
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "admin"
        mock_get_user.return_value = mock_user
        yield mock_get_user


@pytest.fixture
def mock_databases():
    """Create mock database connection objects."""
    db1 = MagicMock()
    db1.id = 1
    db1.database_name = "PostgreSQL Production"
    db1.backend = "postgresql"
    db1.allow_dml = True
    db1.expose_in_sqllab = True

    db2 = MagicMock()
    db2.id = 2
    db2.database_name = "Dremio Analytics"
    db2.backend = "dremio"
    db2.allow_dml = False
    db2.expose_in_sqllab = True

    db3 = MagicMock()
    db3.id = 3
    db3.database_name = "MySQL Reporting"
    db3.backend = "mysql"
    db3.allow_dml = True
    db3.expose_in_sqllab = False

    return [db1, db2, db3]


@pytest.mark.asyncio
async def test_list_databases_success(mock_databases):
    """Test successful database connection listing."""
    mock_ctx = MagicMock()
    mock_ctx.info = MagicMock(return_value=None)

    request = ListDatabasesRequest()

    with patch("superset.mcp_service.database.tool.list_databases.DatabaseDAO") as mock_dao:
        mock_dao.find_all.return_value = mock_databases

        result = await list_databases(mock_ctx, request)

        assert result.success is True
        assert result.count == 3
        assert len(result.databases) == 3

        # Check first database
        assert result.databases[0]["id"] == 1
        assert result.databases[0]["name"] == "PostgreSQL Production"
        assert result.databases[0]["backend"] == "postgresql"
        assert result.databases[0]["allow_dml"] is True
        assert result.databases[0]["expose_in_sqllab"] is True

        # Check second database
        assert result.databases[1]["id"] == 2
        assert result.databases[1]["name"] == "Dremio Analytics"
        assert result.databases[1]["backend"] == "dremio"

        # Check third database
        assert result.databases[2]["id"] == 3
        assert result.databases[2]["name"] == "MySQL Reporting"
        assert result.databases[2]["backend"] == "mysql"


@pytest.mark.asyncio
async def test_list_databases_empty():
    """Test listing database connections when none exist."""
    mock_ctx = MagicMock()
    mock_ctx.info = MagicMock(return_value=None)

    request = ListDatabasesRequest()

    with patch("superset.mcp_service.database.tool.list_databases.DatabaseDAO") as mock_dao:
        mock_dao.find_all.return_value = []

        result = await list_databases(mock_ctx, request)

        assert result.success is True
        assert result.count == 0
        assert len(result.databases) == 0
        assert "0 database" in result.message


@pytest.mark.asyncio
async def test_list_databases_error():
    """Test error handling when database fetch fails."""
    mock_ctx = MagicMock()
    mock_ctx.info = MagicMock(return_value=None)
    mock_ctx.error = MagicMock(return_value=None)

    request = ListDatabasesRequest()

    with patch("superset.mcp_service.database.tool.list_databases.DatabaseDAO") as mock_dao:
        mock_dao.find_all.side_effect = Exception("Connection failed")

        result = await list_databases(mock_ctx, request)

        assert result.success is False
        assert result.count == 0
        assert len(result.databases) == 0
        assert "Failed to list database connections" in result.error
        assert "Connection failed" in result.error
