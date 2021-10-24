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

__all__ = ["RAM"]


class RAM:
    def __init__(self, session: boto3.Session, region: str) -> None:
        self.client = session.client("ram", region_name=region)
        self.region = region

    def enable_sharing_with_aws_organization(self) -> None:
        """
        Enable Resource Access Manager sharing with organization

        Executes in: management account in all regions
        """

        logger.info(f"[{self.region}] Enabling RAM sharing with organization")
        try:
            self.client.enable_sharing_with_aws_organization()
            logger.debug(f"[{self.region}] Enabled RAM sharing with organization")
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] != "OperationNotPermittedException":
                logger.exception(
                    f"[{self.region}] Unable enable RAM sharing with organization"
                )
                raise error
