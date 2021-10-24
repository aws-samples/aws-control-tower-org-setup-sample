#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
* Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
* SPDX-License-Identifier: MIT-0
*
* Permission is hereby granted, free of charge, to any person obtaining a copy of this
* software and associated documentation files (the "Software"), to deal in the Software
* without restriction, including without limitation the rights to use, copy, modify,
* merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
* permit persons to whom the Software is furnished to do so.
*
* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
* INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
* PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
* HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
* OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
* SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from aws_lambda_powertools import Logger
import boto3
import botocore

logger = Logger(child=True)

__all__ = ["ServiceCatalog"]


class ServiceCatalog:
    def __init__(self, session: boto3.Session, region: str) -> None:
        self.client = session.client("servicecatalog", region_name=region)
        self.region = region

    def enable_aws_organizations_access(self) -> None:
        """
        Enable Service Catalog sharing with organization

        Executes in: management account in all regions
        """
        logger.info(
            f"[{self.region}] Enabling organizational access for Service Catalog"
        )
        try:
            self.client.enable_aws_organizations_access()
            logger.debug(
                f"[{self.region}] Enabled organizational access for Service Catalog"
            )
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] != "InvalidStateException":
                logger.exception(
                    f"[{self.region}] Unable to enable organization access for Service Catalog"
                )
                raise error
