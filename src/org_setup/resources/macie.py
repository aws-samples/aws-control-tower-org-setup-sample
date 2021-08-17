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

logger = Logger(child=True)

__all__ = ["Macie"]


class Macie:
    def __init__(self, session: boto3.Session, region: str) -> None:
        self.session = session
        self.client = session.client("macie2", region_name=region)
        self.region = region

    def enable_organization_admin_account(self, account_id: str) -> None:
        logger.info(
            f"Enabling account {account_id} to be Macie admin account in {self.region}"
        )
        try:
            self.client.enable_organization_admin_account(adminAccountId=account_id)
            logger.debug(
                f"Enabled account {account_id} to be Macie admin account in {self.region}"
            )
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] != "ConflictException":
                logger.exception(
                    f"Unable to enable account {account_id} to be Macie admin account in {self.region}"
                )
                raise error

    def update_organization_configuration(self, account_id: str) -> None:
        """
        Update the organization configuration to auto-enroll new accounts in Macie
        """
        assumed_role_session = STS(self.session).assume_role(
            account_id, "macie_org_config"
        )

        client = assumed_role_session.client("macie2", region_name=self.region)
        client.update_organization_configuration(autoEnable=True)
