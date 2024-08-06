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

from typing import List, Dict, TYPE_CHECKING

from aws_lambda_powertools import Logger
import boto3
import botocore

if TYPE_CHECKING:
    from mypy_boto3_guardduty import GuardDutyClient, ListDetectorsPaginator

from ..constants import BOTO3_CONFIG

logger = Logger(child=True)

__all__ = ["GuardDuty"]


class GuardDuty:
    def __init__(self, session: boto3.Session, region: str) -> None:
        self.client: "GuardDutyClient" = session.client(
            "guardduty", region_name=region, config=BOTO3_CONFIG
        )
        self.region = region

    def enable_organization_admin_account(self, account_id: str) -> None:
        """
        Delegate GuardDuty administration to an account

        Executes in: management account in all regions
        """

        logger.info(
            f"Delegating GuardDuty administration to account {account_id}", region=self.region
        )
        try:
            self.client.enable_organization_admin_account(AdminAccountId=account_id)
            logger.debug(
                f"Delegated GuardDuty administration to account {account_id}", region=self.region
            )
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] != "BadRequestException":
                logger.exception(
                    f"Unable to delegate GuardDuty administration to account {account_id}",
                    region=self.region,
                )
                raise error

    def create_detector(self) -> List[str]:
        """
        Update the organization configuration to auto-enroll new accounts in GuardDuty

        Executes in: delegated administrator account in all regions
        """

        detector_ids: List[str] = []

        paginator: "ListDetectorsPaginator" = self.client.get_paginator("list_detectors")
        page_iterator = paginator.paginate()
        for page in page_iterator:
            detector_ids.extend(page.get("DetectorIds", []))

        if detector_ids:
            for detector_id in detector_ids:
                self.client.update_detector(
                    DetectorId=detector_id,
                    Enable=True,
                    FindingPublishingFrequency="FIFTEEN_MINUTES",
                    Features=[
                        {
                            "Name": "S3_DATA_EVENTS",
                            "Status": "ENABLED",
                        },
                        {
                            "Name": "EKS_AUDIT_LOGS",
                            "Status": "ENABLED",
                        },
                        {
                            "Name": "EBS_MALWARE_PROTECTION",
                            "Status": "ENABLED",
                        },
                        {
                            "Name": "RDS_LOGIN_EVENTS",
                            "Status": "ENABLED",
                        },
                        {
                            "Name": "LAMBDA_NETWORK_LOGS",
                            "Status": "ENABLED",
                        },
                        {
                            "Name": "RUNTIME_MONITORING",
                            "Status": "ENABLED",
                            "AdditionalConfiguration": [
                                {
                                    "Name": "EKS_ADDON_MANAGEMENT",
                                    "Status": "ENABLED",
                                },
                                {
                                    "Name": "ECS_FARGATE_AGENT_MANAGEMENT",
                                    "Status": "ENABLED",
                                },
                                {
                                    "Name": "EC2_AGENT_MANAGEMENT",
                                    "Status": "ENABLED",
                                },
                            ],
                        },
                    ],
                )
        else:
            response = self.client.create_detector(
                Enable=True,
                FindingPublishingFrequency="FIFTEEN_MINUTES",
                Features=[
                    {
                        "Name": "S3_DATA_EVENTS",
                        "Status": "ENABLED",
                    },
                    {
                        "Name": "EKS_AUDIT_LOGS",
                        "Status": "ENABLED",
                    },
                    {
                        "Name": "EBS_MALWARE_PROTECTION",
                        "Status": "ENABLED",
                    },
                    {
                        "Name": "RDS_LOGIN_EVENTS",
                        "Status": "ENABLED",
                    },
                    {
                        "Name": "LAMBDA_NETWORK_LOGS",
                        "Status": "ENABLED",
                    },
                    {
                        "Name": "RUNTIME_MONITORING",
                        "Status": "ENABLED",
                        "AdditionalConfiguration": [
                            {
                                "Name": "EKS_ADDON_MANAGEMENT",
                                "Status": "ENABLED",
                            },
                            {
                                "Name": "ECS_FARGATE_AGENT_MANAGEMENT",
                                "Status": "ENABLED",
                            },
                            {
                                "Name": "EC2_AGENT_MANAGEMENT",
                                "Status": "ENABLED",
                            },
                        ],
                    },
                ],
            )
            detector_ids.append(response["DetectorId"])

        for detector_id in detector_ids:
            self.client.update_organization_configuration(
                DetectorId=detector_id,
                Features=[
                    {
                        "Name": "S3_DATA_EVENTS",
                        "AutoEnable": "NEW",
                    },
                    {
                        "Name": "EKS_AUDIT_LOGS",
                        "AutoEnable": "NEW",
                    },
                    {
                        "Name": "EBS_MALWARE_PROTECTION",
                        "AutoEnable": "NEW",
                    },
                    {
                        "Name": "RDS_LOGIN_EVENTS",
                        "AutoEnable": "NEW",
                    },
                    {
                        "Name": "LAMBDA_NETWORK_LOGS",
                        "AutoEnable": "NEW",
                    },
                    {
                        "Name": "RUNTIME_MONITORING",
                        "AutoEnable": "NEW",
                        "AdditionalConfiguration": [
                            {
                                "Name": "EKS_ADDON_MANAGEMENT",
                                "AutoEnable": "NEW",
                            },
                            {
                                "Name": "ECS_FARGATE_AGENT_MANAGEMENT",
                                "AutoEnable": "NEW",
                            },
                            {
                                "Name": "EC2_AGENT_MANAGEMENT",
                                "AutoEnable": "NEW",
                            },
                        ],
                    },
                ],
                AutoEnableOrganizationMembers="ALL",
            )

        logger.info("Updated GuardDuty to auto-enroll new accounts", region=self.region)

        return detector_ids

    def create_members(self, detector_ids: List[str], accounts: List[Dict[str, str]]) -> None:
        """
        Create members in GuardDuty
        """
        for detector_id in detector_ids:
            self.client.create_members(DetectorId=detector_id, AccountDetails=accounts)
