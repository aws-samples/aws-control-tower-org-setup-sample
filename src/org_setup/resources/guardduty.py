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

logger = Logger(child=True)

__all__ = ["GuardDuty"]


class GuardDuty:
    def __init__(self, session: boto3.Session, region: str) -> None:
        self.client = session.client("guardduty", region_name=region)
        self.region = region

    def enable_organization_admin_account(self, account_id: str) -> None:
        """
        Delegate GuardDuty administration to an account

        Executes in: management account in all regions
        """

        logger.info(
            f"[{self.region}] Delegating GuardDuty administration to account {account_id}"
        )
        try:
            self.client.enable_organization_admin_account(AdminAccountId=account_id)
            logger.debug(
                f"[{self.region}] Delegated GuardDuty administration to account {account_id}"
            )
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] != "BadRequestException":
                logger.exception(
                    f"[{self.region}] Unable to delegate GuardDuty administration to account {account_id}"
                )
                raise error

    def create_detector(self) -> List[str]:
        """
        Update the organization configuration to auto-enroll new accounts in GuardDuty

        Executes in: delegated administrator account in all regions
        """

        detector_ids = []

        paginator = self.client.get_paginator("list_detectors")
        page_iterator = paginator.paginate()
        for page in page_iterator:
            detector_ids.extend(page.get("DetectorIds", []))

        if detector_ids:
            for detector_id in detector_ids:
                self.client.update_detector(
                    DetectorId=detector_id,
                    Enable=True,
                    FindingPublishingFrequency="FIFTEEN_MINUTES",
                    DataSources={"S3Logs": {"Enable": True}},
                )
        else:
            response = self.client.create_detector(
                Enable=True,
                DataSources={"S3Logs": {"Enable": True}},
                FindingPublishingFrequency="FIFTEEN_MINUTES",
            )
            detector_ids.append(response["DetectorId"])

        for detector_id in detector_ids:
            self.client.update_organization_configuration(
                DetectorId=detector_id,
                AutoEnable=True,
                DataSources={"S3Logs": {"AutoEnable": True}},
            )

        logger.info(f"[{self.region}] Updated GuardDuty to auto-enroll new accounts")

        return detector_ids

    def create_members(
        self, detector_ids: List[str], accounts: List[Dict[str, str]]
    ) -> None:
        """
        Create members in GuardDuty
        """
        for detector_id in detector_ids:
            self.client.create_members(DetectorId=detector_id, AccountDetails=accounts)
