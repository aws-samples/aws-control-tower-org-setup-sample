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

from typing import List, Dict

from aws_lambda_powertools import Logger
import boto3
import botocore

from ..constants import BOTO3_CONFIG

logger = Logger(child=True)

__all__ = ["Macie"]


class Macie:
    def __init__(self, session: boto3.Session, region: str) -> None:
        self.client = session.client("macie2", region_name=region, config=BOTO3_CONFIG)
        self.region = region

    def enable_macie(self) -> None:
        """
        Enable Macie

        Executes in: management account in all regions
        """

        logger.info("Enabling Macie", region=self.region)
        try:
            self.client.enable_macie(findingPublishingFrequency="FIFTEEN_MINUTES", status="ENABLED")
            logger.debug("Enabled Macie", region=self.region)
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] != "ConflictException":
                logger.exception("Unable to enable Macie", region=self.region)
                raise error

    def enable_organization_admin_account(self, account_id: str) -> None:
        """
        Delegate Macie administration to an account

        Executes in: management account in all regions
        """

        logger.info(f"Delegating Macie administration to account {account_id}", region=self.region)
        try:
            self.client.enable_organization_admin_account(adminAccountId=account_id)
            logger.debug(
                f"Delegated Macie administration to account {account_id}", region=self.region
            )
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] != "ConflictException":
                logger.exception(
                    f"Unable to delegate Macie administration to account {account_id}",
                    region=self.region,
                )
                raise error

    def update_organization_configuration(self) -> None:
        """
        Update the organization configuration to auto-enroll new accounts in Macie

        Executes in: delegated administrator account in all regions
        """

        self.client.update_organization_configuration(autoEnable=True)
        logger.info("Updated Macie to auto-enroll new accounts", region=self.region)

    def create_members(self, accounts: List[Dict[str, str]]) -> None:
        """
        Create members in Macie
        """
        for account in accounts:
            try:
                self.client.create_member(
                    account={
                        "accountId": account["AccountId"],
                        "email": account["Email"],
                    }
                )
            except botocore.exceptions.ClientError as error:
                if error.response["Error"]["Code"] != "ValidationException":
                    logger.exception("Unable to create Macie member", region=self.region)
                    raise error
