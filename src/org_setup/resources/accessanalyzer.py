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

from ..constants import ORGANIZATION_ANALYZER_NAME, MANAGEMENT_ANALYZER_NAME, BOTO3_CONFIG

logger = Logger(child=True)

__all__ = ["AccessAnalyzer"]


class AccessAnalyzer:
    def __init__(self, session: boto3.Session, region: str) -> None:
        self.client = session.client("accessanalyzer", region_name=region, config=BOTO3_CONFIG)
        self.region = region

    def create_management_analyzer(self) -> None:
        """
        Create an account IAM access analyzer for the management account

        Executes in: management account in all regions
        """

        logger.info("Creating account IAM access analyzer", region=self.region)
        try:
            self.client.create_analyzer(analyzerName=MANAGEMENT_ANALYZER_NAME, type="ACCOUNT")
            logger.debug("Created account IAM access analyzer", region=self.region)
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] != "ConflictException":
                logger.exception(
                    "Unable to create an account IAM access analyzer", region=self.region
                )
                raise error

    def create_org_analyzer(self) -> None:
        """
        Create an organizational IAM access analyzer

        Executes in: delegated administrator account in all regions
        """

        logger.info("Creating organizational IAM access analyzer", region=self.region)
        try:
            self.client.create_analyzer(
                analyzerName=ORGANIZATION_ANALYZER_NAME, type="ORGANIZATION"
            )
            logger.debug("Created organizational IAM access analyzer", region=self.region)
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] != "ConflictException":
                logger.exception(
                    "Unable to create an organizational IAM access analyzer", region=self.region
                )
                raise error
