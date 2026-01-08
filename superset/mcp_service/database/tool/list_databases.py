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

"""
List database connections FastMCP tool

This module provides the MCP tool for listing all available database connections
in Superset. These are the data sources that you can create datasets from.
"""

import logging

from fastmcp import Context
from superset_core.mcp import tool

from superset.daos.database import DatabaseDAO
from superset.mcp_service.database.schemas import (
    ListDatabasesRequest,
    ListDatabasesResponse,
)
from superset.mcp_service.utils.schema_utils import parse_request

logger = logging.getLogger(__name__)


@tool()
@parse_request(ListDatabasesRequest)
async def list_databases(
    request: ListDatabasesRequest,
    ctx: Context,
) -> ListDatabasesResponse:
    """
    List all available database connections in Superset.

    This tool shows all database connections configured in Superset.
    These are the data sources (PostgreSQL, MySQL, Dremio, etc.) that
    you connect to Superset. You can then create datasets FROM these
    database connections.

    Use this tool to:
    - Discover available database connections
    - Find the correct database name to use in create_dataset
    - Check database permissions (DML, SQL Lab access)

    Args:
        ctx: FastMCP context for logging and progress reporting
        request: List databases request (no parameters needed)

    Returns:
        ListDatabasesResponse with list of database connections

    Example:
        >>> # List all database connections
        >>> result = await list_databases(ctx, {})
        >>> for db in result.databases:
        ...     print(f"{db.name} (ID: {db.id}, Type: {db.backend})")
        PostgreSQL Production (ID: 1, Type: postgresql)
        Dremio Analytics (ID: 2, Type: dremio)
    """
    try:
        await ctx.info("Fetching all database connections from Superset")

        # Get all database connections (skip_base_filter=True to bypass RBAC)
        # MCP tools run with admin context, so we want to see all databases
        databases = DatabaseDAO.find_all(skip_base_filter=True)

        # Convert to response format - access all attributes while objects are still
        # attached to the session to avoid DetachedInstanceError
        database_list = []
        for db in databases:
            database_list.append({
                "id": db.id,
                "name": db.database_name,
                "backend": db.backend,
                "allow_dml": db.allow_dml,
                "expose_in_sqllab": db.expose_in_sqllab,
            })

        await ctx.info(f"Found {len(database_list)} database connections")

        return ListDatabasesResponse(
            success=True,
            databases=database_list,
            count=len(database_list),
            message=f"Successfully retrieved {len(database_list)} database connections",
        )

    except Exception as e:
        error_message = f"Failed to list database connections: {str(e)}"
        logger.exception("Error in list_databases tool")
        await ctx.error(error_message)

        return ListDatabasesResponse(
            success=False,
            databases=[],
            count=0,
            error=error_message,
            message="Failed to retrieve database connections",
        )
