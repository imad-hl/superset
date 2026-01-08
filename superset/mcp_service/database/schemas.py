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

"""Schemas for database MCP tools."""

from typing import Annotated, List

from pydantic import BaseModel, ConfigDict, Field


class ListDatabasesRequest(BaseModel):
    """Request to list all available database connections."""

    model_config = ConfigDict(extra="forbid")


class DatabaseInfo(BaseModel):
    """Information about a database connection."""

    id: Annotated[int, Field(description="Database connection ID")]
    name: Annotated[str, Field(description="Database connection name")]
    backend: Annotated[
        str, Field(description="Database backend/engine (e.g., postgresql, dremio, mysql)")
    ]
    allow_dml: Annotated[
        bool, Field(description="Whether DML operations (INSERT, UPDATE, DELETE) are allowed")
    ]
    expose_in_sqllab: Annotated[
        bool, Field(description="Whether this database is exposed in SQL Lab")
    ]


class ListDatabasesResponse(BaseModel):
    """Response from listing database connections."""

    success: Annotated[bool, Field(description="Whether the operation succeeded")]
    databases: Annotated[
        List[DatabaseInfo], Field(description="List of available database connections")
    ]
    count: Annotated[int, Field(description="Number of database connections returned")]
    message: Annotated[str | None, Field(default=None, description="Response message")]
    error: Annotated[
        str | None, Field(default=None, description="Error message if failed")
    ]
