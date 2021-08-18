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

__all__ = ["GuardDuty"]


class GuardDuty:
    def __init__(self, session: boto3.Session, region: str) -> None:
        self.session = session
        self.client = session.client("guardduty", region_name=region)
        self.region = region

    def enable_organization_admin_account(self, account_id: str) -> None:
        logger.info(
            f"[{self.region}] Enabling account {account_id} to be GuardDuty admin account"
        )
        try:
            self.client.enable_organization_admin_account(AdminAccountId=account_id)
            logger.debug(
                f"[{self.region}] Enabled account {account_id} to be GuardDuty admin account"
            )
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] != "BadRequestException":
                logger.exception(
                    f"[{self.region}] Unable to enable account {account_id} to be GuardDuty admin account"
                )
                raise error

    def update_organization_configuration(self, account_id: str) -> None:
        """
        Update the organization configuration to auto-enroll new accounts in GuardDuty
        """

        assumed_role_session = STS(self.session).assume_role(
            account_id, "guardduty_org_config"
        )

        client = assumed_role_session.client("guardduty", region_name=self.region)

        detector_ids = []

        paginator = client.get_paginator("list_detectors")
        page_iterator = paginator.paginate()
        for page in page_iterator:
            detector_ids.extend(page.get("DetectorIds", []))

        if not detector_ids:
            response = client.create_detector(
                Enable=True,
                DataSources={"S3Logs": {"Enable": True}},
                FindingPublishingFrequency="SIX_HOURS",
            )
            detector_ids.append(response["DetectorId"])

        for detector_id in detector_ids:
            client.update_organization_configuration(
                DetectorId=detector_id,
                AutoEnable=True,
                DataSources={"S3Logs": {"AutoEnable": True}},
            )
