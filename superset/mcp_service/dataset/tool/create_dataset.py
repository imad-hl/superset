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
Create dataset FastMCP tool

This module provides the MCP tool for creating new datasets (both physical table-based
and virtual SQL-based datasets) in Superset.
"""

import logging
from typing import TYPE_CHECKING

from fastmcp import Context
from marshmallow import ValidationError
from superset_core.mcp import tool

if TYPE_CHECKING:
    from superset.connectors.sqla.models import SqlaTable

from superset.commands.dataset.create import CreateDatasetCommand
from superset.commands.dataset.exceptions import (
    DatasetCreateFailedError,
    DatasetInvalidError,
)
from superset.mcp_service.dataset.schemas import (
    CreateDatasetRequest,
    CreateDatasetResponse,
    serialize_dataset_object,
)
from superset.mcp_service.utils.schema_utils import parse_request

logger = logging.getLogger(__name__)


@tool(tags=["mutate"])
@parse_request(CreateDatasetRequest)
async def create_dataset(
    request: CreateDatasetRequest, ctx: Context
) -> CreateDatasetResponse:
    """Create a new dataset in Superset (physical table or virtual SQL-based).

    This tool creates datasets that can be used for creating charts and dashboards.
    Datasets can be:
    - Physical: Based on existing database tables (requires schema + table_name)
    - Virtual: Based on SQL queries (requires sql parameter)

    IMPORTANT BEHAVIORS:
    - Database: Use EITHER database_id (numeric) OR database_name (string)
    - Physical tables: MUST specify schema parameter
    - Virtual datasets: MUST specify sql parameter
    - Automatically fetches metadata (columns, metrics) unless fetch_metadata=False
    - Returns the created dataset with full details including ID and UUID

    Example using database_name (recommended):
    ```json
    {
        "database_name": "PostgreSQL Production",
        "table_name": "sales_data",
        "schema": "public",
        "description": "Sales transactions table"
    }
    ```

    Example using database_id:
    ```json
    {
        "database_id": 1,
        "table_name": "sales_data",
        "schema": "public",
        "description": "Sales transactions table"
    }
    ```

    Example for virtual dataset (SQL-based):
    ```json
    {
        "database_id": 1,
        "table_name": "Top 10 Products",
        "sql": "SELECT product_name, SUM(revenue) as total_revenue FROM sales GROUP BY product_name ORDER BY total_revenue DESC LIMIT 10",
        "description": "Top selling products"
    }
    ```

    VALIDATION:
    - Database must exist
    - For physical tables: table must exist in database
    - For virtual datasets: SQL must be valid and user must have access to all tables
    - Dataset name must be unique within the database/schema
    - User must have permissions to create datasets

    Returns:
    - Dataset ID and metadata
    - Column and metric information (if fetch_metadata=True)
    - Validation errors with suggestions if creation fails
    """
    try:
        # Resolve database_name to database_id if needed
        database_id = request.database_id
        if request.database_name:
            await ctx.debug(
                "Resolving database name to ID: database_name=%s" % (request.database_name,)
            )
            from superset.daos.database import DatabaseDAO

            database = DatabaseDAO.get_database_by_name(request.database_name)
            if not database:
                return CreateDatasetResponse(
                    success=False,
                    message=f"Database '{request.database_name}' not found",
                    error=f"No database found with name '{request.database_name}'. "
                    "Please check the database name and try again.",
                )
            database_id = database.id
            await ctx.debug(
                "Resolved database: database_id=%s, database_name=%s"
                % (database_id, request.database_name)
            )

        await ctx.info(
            "Creating dataset: database_id=%s, table_name=%s, schema=%s, is_virtual=%s"
            % (
                database_id,
                request.table_name,
                request.schema_name,
                bool(request.sql),
            )
        )

        if request.sql:
            await ctx.debug("Creating virtual dataset with SQL: sql=%s" % (request.sql[:100],))
        else:
            await ctx.debug(
                "Creating physical dataset: schema=%s, table=%s"
                % (request.schema_name, request.table_name)
            )

        # Build command payload
        command_data = {
            "database": database_id,
            "table_name": request.table_name,
        }

        # Add optional fields
        if request.schema_name:
            command_data["schema"] = request.schema_name
        if request.sql:
            command_data["sql"] = request.sql
        if request.catalog:
            command_data["catalog"] = request.catalog
        if request.description:
            command_data["description"] = request.description
        if request.owner_ids:
            command_data["owners"] = request.owner_ids

        await ctx.report_progress(1, 3, "Validating dataset creation request")

        # Execute create command
        command = CreateDatasetCommand(command_data)
        dataset: "SqlaTable" = command.run()

        await ctx.report_progress(2, 3, "Dataset created successfully")

        # Fetch metadata if requested (columns, metrics)
        if request.fetch_metadata and dataset:
            await ctx.debug("Fetching dataset metadata (columns and metrics)")
            try:
                dataset.fetch_metadata()
            except Exception as metadata_error:
                await ctx.warning(
                    "Failed to fetch metadata: %s" % (str(metadata_error),)
                )

        await ctx.report_progress(3, 3, "Serializing dataset response")

        # Serialize the dataset
        dataset_info = serialize_dataset_object(dataset)

        success_message = (
            f"Dataset '{request.table_name}' created successfully "
            f"(ID: {dataset.id}, UUID: {dataset.uuid})"
        )

        await ctx.info(success_message)

        return CreateDatasetResponse(
            success=True,
            dataset=dataset_info,
            message=success_message,
        )

    except DatasetInvalidError as e:
        # Handle validation errors
        validation_errors = []
        error_message = "Dataset validation failed"

        # Log the full exception for debugging
        await ctx.debug(
            "DatasetInvalidError details: %s, exceptions: %s" 
            % (str(e), getattr(e, "exceptions", None))
        )

        if hasattr(e, "exceptions") and e.exceptions:
            for exc in e.exceptions:
                if isinstance(exc, ValidationError):
                    # Extract validation error messages
                    if hasattr(exc, "messages"):
                        if isinstance(exc.messages, dict):
                            for field, msgs in exc.messages.items():
                                if isinstance(msgs, list):
                                    validation_errors.extend(
                                        [f"{field}: {msg}" for msg in msgs]
                                    )
                                else:
                                    validation_errors.append(f"{field}: {msgs}")
                        elif isinstance(exc.messages, list):
                            validation_errors.extend(exc.messages)
                        else:
                            validation_errors.append(str(exc.messages))
                    else:
                        validation_errors.append(str(exc))
                else:
                    # Include the exception type and message
                    exc_type = type(exc).__name__
                    validation_errors.append(f"{exc_type}: {str(exc)}")

        if not validation_errors:
            validation_errors = [str(e)]

        error_message = "; ".join(validation_errors)

        await ctx.error("Dataset validation failed: %s" % (error_message,))

        return CreateDatasetResponse(
            success=False,
            message="Dataset creation failed due to validation errors",
            error=error_message,
            validation_errors=validation_errors,
        )

    except DatasetCreateFailedError as e:
        error_message = str(e)
        await ctx.error("Dataset creation failed: %s" % (error_message,))

        return CreateDatasetResponse(
            success=False,
            message="Dataset creation failed",
            error=error_message,
        )

    except Exception as e:
        error_message = f"Unexpected error during dataset creation: {str(e)}"
        logger.exception("Unexpected error in create_dataset tool")
        await ctx.error(error_message)

        return CreateDatasetResponse(
            success=False,
            message="Dataset creation failed due to unexpected error",
            error=error_message,
        )
