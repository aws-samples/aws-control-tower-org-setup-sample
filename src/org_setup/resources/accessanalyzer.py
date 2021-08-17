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

from .sts import STS
from ..constants import ORGANIZATION_ANALYZER_NAME

logger = Logger(child=True)

__all__ = ["AccessAnalyzer"]


class AccessAnalyzer:
    def __init__(self, session: boto3.Session) -> None:
        self.client = session.client("accessanalyzer")

    def create_analyzer(self, analyzer_name: str, analyzer_type: str) -> None:
        """
        Create an IAM access analyzer
        """

        try:
            self.client.create_analyzer(analyzerName=analyzer_name, type=analyzer_type)
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] != "ConflictException":
                logger.exception("Unable to create IAM access analyzer")
                raise error

    @classmethod
    def create_org_analyzer(cls, session: boto3.Session, account_id: str) -> None:
        """
        Create an organization IAM access analyzer in the desired account
        """

        assumed_role_session = STS(session).assume_role(account_id, "accessanalyzer")

        client = cls(assumed_role_session)

        logger.info(
            f"Creating organizational IAM access analyzer in account {account_id}"
        )
        client.create_analyzer(ORGANIZATION_ANALYZER_NAME, "ORGANIZATION")
        logger.debug(
            f"Created organizational IAM access analyzer in account {account_id}"
        )
