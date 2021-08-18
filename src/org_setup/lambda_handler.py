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

import os
from typing import Dict, Any, List

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3
from crhelper import CfnResource

from .constants import SERVICE_ACCESS_PRINCIPALS, DELEGATED_ADMINISTRATOR_PRINCIPALS
from .resources import (
    AccessAnalyzer,
    AuditManager,
    EC2,
    FMS,
    GuardDuty,
    Macie,
    Organizations,
    RAM,
    SecurityHub,
    ServiceCatalog,
)

helper = CfnResource(json_logging=True, log_level="INFO", boto_level="INFO")

try:
    ADMINISTRATOR_ACCOUNT_NAME = os.environ["ADMINISTRATOR_ACCOUNT_NAME"]
    REGIONS = os.getenv("REGIONS", "").split(",")
    REGIONS = list(filter(None, REGIONS))  # remove empty strings
    ENABLE_AI_OPTOUT_POLICY: bool = (
        os.getenv("ENABLE_AI_OPTOUT_POLICY", False) == "true"
    )
    tracer = Tracer()
    logger = Logger()
except Exception as exc:
    helper.init_failure(exc)


@tracer.capture_method
def setup_organization(
    admin_account_id: str = None,
) -> None:
    """
    Set up the organization in multiple regions
    """

    session = boto3.Session()
    organizations = Organizations(session)
    org = organizations.describe_organization()
    org_id: str = org["Id"]

    logger.info(f"Configuring organization {org_id} in regions: {REGIONS}")

    # enable all organizational features
    organizations.enable_all_features()

    # enable all organizational policy types
    organizations.enable_all_policy_types()

    if ENABLE_AI_OPTOUT_POLICY:
        # attach an AI service opt-out policy
        organizations.attach_ai_optout_policy()

    # enable Service Catalog access to the organization
    ServiceCatalog(session).enable_aws_organizations_access()

    # enable various AWS service principal access to the organization
    organizations.enable_aws_service_access(SERVICE_ACCESS_PRINCIPALS)

    # enable RAM sharing to the organization
    RAM(session).enable_sharing_with_aws_organization()

    if not admin_account_id:
        admin_account_id = organizations.get_account_id(ADMINISTRATOR_ACCOUNT_NAME)
        if not admin_account_id:
            logger.warning(
                f'No administrator account found named "{ADMINISTRATOR_ACCOUNT_NAME}"'
            )
            return

    # Register the administrator account as a delegated administer on AWS services
    organizations.register_delegated_administrator(
        admin_account_id, DELEGATED_ADMINISTRATOR_PRINCIPALS
    )

    logger.info(f"Delegating IAM Access Analyzer administration to {admin_account_id}")

    # Create organization IAM access analyzer in the administrator account
    AccessAnalyzer.create_org_analyzer(session, admin_account_id)

    logger.info(f"Delegating Firewall Manager administration to {admin_account_id}")

    # Delegate Firewall Manager to the administrator account
    FMS(session).associate_admin_account(admin_account_id)

    global REGIONS
    if not REGIONS:
        REGIONS = EC2(session).get_all_regions()

    for region in REGIONS:
        logger.info(
            f"[{region}] Delegating Security Hub administration to {admin_account_id}"
        )

        securityhub = SecurityHub(session, region)

        # delegate SecurityHub administration to the administrator account
        securityhub.enable_organization_admin_account(admin_account_id)

        # update the SecurityHub organization configuration to register new accounts automatically
        securityhub.update_organization_configuration(admin_account_id)

        logger.info(
            f"[{region}] Delegating GuardDuty administration to {admin_account_id}"
        )

        guardduty = GuardDuty(session, region)

        # delegate GuardDuty administration to the administrator account
        guardduty.enable_organization_admin_account(admin_account_id)

        # update the GuartDuty organization configuration to register new accounts automatically
        guardduty.update_organization_configuration(admin_account_id)

        logger.info(f"[{region}] Delegating Macie administration to {admin_account_id}")

        macie = Macie(session, region)

        # delegate Macie administration to the admin_account_id
        macie.enable_organization_admin_account(admin_account_id)

        # update the Macie organization configuration to register new accounts automatically
        macie.update_organization_configuration(admin_account_id)

        logger.info(
            f"[{region}] Delegating Audit Manager administration to {admin_account_id}"
        )

        auditmanager = AuditManager(session, region)

        # delegate Audit Manager administration to the admin_account_id
        auditmanager.register_organization_admin_account(admin_account_id)


@helper.create
@helper.update
def create(event: Dict[str, Any], context: LambdaContext) -> bool:
    logger.info("Got Create or Update")
    setup_organization()


@helper.delete
def delete(event: Dict[str, Any], context: LambdaContext) -> None:
    logger.info("Got Delete")


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def handler(event: Dict[str, Any], context: LambdaContext) -> None:

    # Set up a new landing zone
    if event.get("eventName") == "SetupLandingZone":
        accounts: List[Dict[str, str]] = (
            event.get("serviceEventDetails", {})
            .get("setupLandingZoneStatus", {})
            .get("accounts", [])
        )

        admin_account_id: str = None

        for account in accounts:
            if account["accountName"] == ADMINISTRATOR_ACCOUNT_NAME:
                admin_account_id = account["accountId"]
                break

        return setup_organization(admin_account_id)

    helper(event, context)
