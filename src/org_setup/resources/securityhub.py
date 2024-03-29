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

__all__ = ["SecurityHub"]


class SecurityHub:
    def __init__(self, session: boto3.Session, region: str) -> None:
        self.client = session.client("securityhub", region_name=region, config=BOTO3_CONFIG)
        self.region = region

    def enable_organization_admin_account(self, account_id: str) -> None:
        """
        Delegate SecurityHub administration to an account

        Executes in: management account in each region
        """

        logger.info(
            f"Delegating SecurityHub administration to account {account_id}", region=self.region
        )
        try:
            self.client.enable_organization_admin_account(AdminAccountId=account_id)
            logger.debug(
                f"Delegated SecurityHub administration to account {account_id}", region=self.region
            )
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] != "ResourceConflictException":
                logger.exception(
                    f"Unable to delegate SecurityHub administration to account {account_id}",
                    region=self.region,
                )
                raise error

    def update_configuration(self) -> None:
        """
        Update the organization configuration to auto-enroll new accounts and controls in SecurityHub

        Executes in: delegated administrator account in each region
        """

        logger.info("Auto-enrolling new accounts with SecurityHub", region=self.region)
        self.client.update_organization_configuration(AutoEnable=True)
        logger.info("Auto-enable new security controls", region=self.region)
        self.client.update_security_hub_configuration(AutoEnableControls=True)

    def create_finding_aggregator(self) -> None:
        """
        Create finding aggregator to aggregate findings in the primary region

        Executes in: delegated administrator account in primary region
        """

        response = self.client.list_finding_aggregators()
        aggregators = response["FindingAggregators"]

        if not aggregators:
            logger.info("Creating SecurityHub finding aggregator", region=self.region)
            try:
                self.client.create_finding_aggregator(RegionLinkingMode="ALL_REGIONS")
                logger.debug("Created SecurityHub finding aggregator", region=self.region)
            except botocore.exceptions.ClientError:
                logger.exception(
                    "Unable to create SecurityHub finding aggregator", region=self.region
                )
                raise

    def create_members(self, accounts: List[Dict[str, str]]) -> None:
        """
        Create members in Securityhub
        """
        self.client.create_members(AccountDetails=accounts)
