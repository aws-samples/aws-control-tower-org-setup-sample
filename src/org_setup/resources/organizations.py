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

from functools import lru_cache
import json
from typing import List, Dict, Optional, Any

from aws_lambda_powertools import Logger
import boto3
import botocore

from ..constants import (
    AI_OPT_OUT_POLICY_NAME,
    AI_OPT_OUT_POLICY,
    DELEGATED_ADMINISTRATOR_PRINCIPALS,
    SERVICE_ACCESS_PRINCIPALS,
)
from ..exceptions import OrganizationNotFoundError

logger = Logger(child=True)


__all__ = ["Organizations"]


class Organizations:
    def __init__(self, session: boto3.Session) -> None:
        # must use us-east-1 region with Organizations
        # see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/organizations.html#client
        self.client = session.client(
            "organizations",
            region_name="us-east-1",
            endpoint_url="https://organizations.us-east-1.amazonaws.com",
        )
        self.region = "us-east-1"
        self._roots = []
        self._accounts = []

    def describe_organization(self) -> Dict[str, Any]:
        """
        Describe the organization the account belongs to
        """
        try:
            response = self.client.describe_organization()
        except self.client.exceptions.AWSOrganizationsNotInUseException:
            raise OrganizationNotFoundError()
        except botocore.exceptions.ClientError:
            logger.exception(f"[{self.region}] Unable to describe organization")
            raise
        return response["Organization"]

    def list_accounts(self) -> List[Dict[str, str]]:
        """
        List all of the accounts in an organization
        """
        if self._accounts:
            return self._accounts

        accounts = []

        paginator = self.client.get_paginator("list_accounts")
        page_iterator = paginator.paginate(PaginationConfig={"PageSize": 20})
        for page in page_iterator:
            for account in page.get("Accounts", []):
                if account.get("Status") != "ACTIVE":
                    continue
                accounts.append(account)
        self._accounts = accounts
        return accounts

    def list_policies(self, policy_type: str) -> List[Dict[str, str]]:
        """
        List all of the policies in an organization
        """
        policies = []

        paginator = self.client.get_paginator("list_policies")
        page_iterator = paginator.paginate(Filter=policy_type)
        for page in page_iterator:
            policies.extend(page.get("Policies", []))
        return policies

    def list_roots(self) -> List[Dict[str, str]]:
        """
        List all the roots in an organization
        """
        if self._roots:
            return self._roots

        roots = []

        paginator = self.client.get_paginator("list_roots")
        page_iterator = paginator.paginate()
        for page in page_iterator:
            roots.extend(page.get("Roots", []))

        self._roots = roots
        return roots

    def enable_all_features(self) -> None:
        """
        Enable all features in an organization
        """
        logger.info(f"[{self.region}] Enabling all features in the organization")
        try:
            self.client.enable_all_features()
            logger.debug(f"[{self.region}] Enabled all features in organization")
        except botocore.exceptions.ClientError as error:
            if (
                error.response["Error"]["Code"]
                != "HandshakeConstraintViolationException"
            ):
                logger.exception(
                    f"[{self.region}] Unable to enable all features in organization"
                )
                raise

    def enable_aws_service_access(self) -> None:
        """
        Enable AWS service access in organization
        """
        for principal in SERVICE_ACCESS_PRINCIPALS:
            logger.info(f"[{self.region}] Enabling AWS service access for {principal}")
            try:
                self.client.enable_aws_service_access(ServicePrincipal=principal)
                logger.debug(
                    f"[{self.region}] Enabled AWS service access for {principal}"
                )
            except botocore.exceptions.ClientError as error:
                if error.response["Error"]["Code"] != "ServiceException":
                    logger.exception(
                        f"[{self.region}] Unable enable AWS service access for {principal}"
                    )
                    raise error

    def enable_all_policy_types(self) -> None:
        """
        Enables all policy types in an organization
        """
        logger.info(f"[{self.region}] Enabling all policy types in organization")

        for root in self.list_roots():
            root_id = root["Id"]
            disabled_types = [
                policy_type.get("Type")
                for policy_type in root.get("PolicyTypes", [])
                if policy_type.get("Status") != "ENABLED"
            ]

            for disabled_type in disabled_types:
                logger.info(
                    f"[{self.region}] Enabling policy type {disabled_type} on root {root_id}"
                )
                try:
                    self.client.enable_policy_type(
                        RootId=root_id, PolicyType=disabled_type
                    )
                    logger.debug(
                        f"[{self.region}] Enabled policy type {disabled_type} on root {root_id}"
                    )
                except botocore.exceptions.ClientError as error:
                    if (
                        error.response["Error"]["Code"]
                        != "PolicyTypeAlreadyEnabledException"
                    ):
                        logger.exception(
                            f"[{self.region}] Unable to enable policy type"
                        )
                        raise error

        logger.debug(f"[{self.region}] Enabled all policy types in organization")

    def get_ai_optout_policy(self) -> str:
        """
        Return the AI opt-out policy ID
        """

        for policy in self.list_policies("AISERVICES_OPT_OUT_POLICY"):
            if policy["Name"] == AI_OPT_OUT_POLICY_NAME:
                logger.info(
                    f"[{self.region}] Found existing {AI_OPT_OUT_POLICY_NAME} policy"
                )
                return policy["Id"]

        logger.info(
            f"[{self.region}] {AI_OPT_OUT_POLICY_NAME} policy not found, creating"
        )

        try:
            response = self.client.create_policy(
                Content=json.dumps(AI_OPT_OUT_POLICY),
                Description="Opt-out of all AI services",
                Name=AI_OPT_OUT_POLICY_NAME,
                Type="AISERVICES_OPT_OUT_POLICY",
            )
            policy_id = response.get("Policy", {}).get("PolicySummary", {}).get("Id")
            logger.debug(
                f"[{self.region}] Created policy {AI_OPT_OUT_POLICY_NAME} ({policy_id})"
            )
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] == "DuplicatePolicyException":
                return self.get_ai_optout_policy()
            raise error

        return policy_id

    def attach_ai_optout_policy(self) -> None:
        """
        Attach the AI opt-out policy to the root
        """
        policy_id = self.get_ai_optout_policy()
        if not policy_id:
            logger.warn(
                f"[{self.region}] Unable to find {AI_OPT_OUT_POLICY_NAME} policy"
            )
            return

        for root in self.list_roots():
            root_id = root["Id"]
            logger.info(
                f"[{self.region}] Attaching {AI_OPT_OUT_POLICY_NAME} ({policy_id}) to root {root_id}"
            )
            try:
                self.client.attach_policy(PolicyId=policy_id, TargetId=root_id)
                logger.debug(
                    f"[{self.region}] Attached {AI_OPT_OUT_POLICY_NAME} ({policy_id}) to root {root_id}"
                )
            except botocore.exceptions.ClientError as error:
                if (
                    error.response["Error"]["Code"]
                    != "DuplicatePolicyAttachmentException"
                ):
                    logger.exception(f"[{self.region}] Unable to attach policy")
                    raise error

    def register_delegated_administrators(self, account_id: str) -> None:
        """
        Register delegated administrators
        """

        for principal in DELEGATED_ADMINISTRATOR_PRINCIPALS:
            logger.info(
                f"[{self.region}] Delegating {principal} administration to account {account_id}"
            )
            try:
                self.client.register_delegated_administrator(
                    AccountId=account_id, ServicePrincipal=principal
                )
                logger.debug(
                    f"[{self.region}] Delegated {principal} administration to account {account_id}"
                )
            except botocore.exceptions.ClientError as error:
                if (
                    error.response["Error"]["Code"]
                    != "AccountAlreadyRegisteredException"
                ):
                    logger.exception(
                        f"[{self.region}] Unable to delegate {principal} administration to account {account_id}"
                    )
                    raise error

    @lru_cache
    def get_account_id(self, name: str) -> Optional[str]:
        """
        Return the Account ID for an account
        """
        for account in self.list_accounts():
            if account.get("Name") == name:
                return account["Id"]
        return None
