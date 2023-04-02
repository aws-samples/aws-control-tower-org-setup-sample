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

from concurrent.futures import ThreadPoolExecutor
import os
from typing import Dict, Any, List

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3
from crhelper import CfnResource

from .resources import (
    AccessAnalyzer,
    Detective,
    EC2,
    FMS,
    GuardDuty,
    Inspector,
    Macie,
    Organizations,
    RAM,
    SecurityLake,
    SecurityHub,
    ServiceCatalog,
    STS,
)
from .exceptions import AdministratorAccountNotFoundError

helper = CfnResource(json_logging=True, log_level="INFO", boto_level="INFO")
logger = Logger()

try:
    REGIONS: List[str] = os.getenv("REGIONS", "").split(",")
    REGIONS = list(filter(None, REGIONS))  # remove empty strings
    ADMINISTRATOR_ACCOUNT_NAME: str = os.environ["ADMINISTRATOR_ACCOUNT_NAME"]
    PRIMARY_REGION: str = os.environ["PRIMARY_REGION"]
    ENABLE_AI_OPTOUT_POLICY: bool = os.getenv("ENABLE_AI_OPTOUT_POLICY", False) == "true"
except Exception as exc:
    helper.init_failure(exc)


def setup_region(admin_account_id: str, region: str, accounts: List[Dict[str, str]] = None) -> None:
    """
    Configure services in a region
    """

    management_session = boto3.Session(region_name=region)
    delegate_session = STS(management_session).assume_role(admin_account_id)

    # enable Service Catalog organizational sharing
    ServiceCatalog(management_session, region).enable_aws_organizations_access()

    # enable RAM organizational sharing
    RAM(management_session, region).enable_sharing_with_aws_organization()

    # delegate SecurityHub administration to the administrator account
    SecurityHub(management_session, region).enable_organization_admin_account(admin_account_id)

    # update the SecurityHub organization configuration to register new accounts
    # and security controls automatically
    securityhub = SecurityHub(delegate_session, region)
    securityhub.update_configuration()

    if accounts:
        securityhub.create_members(accounts)

    # delegate GuardDuty administration to the administrator account
    GuardDuty(management_session, region).enable_organization_admin_account(admin_account_id)

    # Create a detector in the administrator account
    guardduty = GuardDuty(delegate_session, region)
    detector_ids = guardduty.create_detector()

    if detector_ids and accounts:
        guardduty.create_members(detector_ids, accounts)

    # delegate Macie administration to the admin_account_id
    macie = Macie(management_session, region)
    macie.enable_macie()
    macie.enable_organization_admin_account(admin_account_id)

    # update the Macie organization configuration to register new accounts automatically
    macie = Macie(delegate_session, region)
    macie.enable_macie()
    macie.update_organization_configuration()

    if accounts:
        macie.create_members(accounts)

    # Delegate Firewall Manager to the administrator account
    FMS(management_session, region).associate_admin_account(admin_account_id)

    # Delegate Detective to the administrator account
    # Detective(management_session, region).enable_organization_admin_account(admin_account_id)

    # Delegate Security Lake to the administrator account
    SecurityLake(management_session, region).create_datalake_delegated_admin(admin_account_id)

    # Delegate Inspector to the administrator account
    Inspector(management_session, region).enable_delegated_admin_account(admin_account_id)

    # Create organization IAM access analyzer in the administrator account
    AccessAnalyzer(delegate_session, region).create_org_analyzer()

    # Create account IAM access analyzer in the management account
    AccessAnalyzer(management_session, region).create_management_analyzer()


def setup_organization(
    primary_region: str, admin_account_id: str = None, regions: List[str] = None
) -> None:
    """
    Set up the organization in multiple regions
    """

    management_session = boto3.Session()
    organizations = Organizations(management_session)
    org = organizations.describe_organization()
    org_id: str = org["Id"]

    if not regions:
        regions = EC2(management_session, primary_region).get_all_regions()

    logger.info(f"Configuring organization {org_id} in regions: {regions}", region=primary_region)

    # enable all organizational features
    organizations.enable_all_features()

    # enable all organizational policy types
    organizations.enable_all_policy_types()

    if ENABLE_AI_OPTOUT_POLICY:
        # attach an AI service opt-out policy
        organizations.attach_ai_optout_policy()

    # enable various AWS service principal access to the organization
    organizations.enable_aws_service_access()

    if not admin_account_id:
        admin_account_id = organizations.get_account_id(ADMINISTRATOR_ACCOUNT_NAME)
        if not admin_account_id:
            raise AdministratorAccountNotFoundError(
                f"Administrator account '{ADMINISTRATOR_ACCOUNT_NAME}' not found"
            )

    # Register the administrator account as a delegated administer on AWS services
    organizations.register_delegated_administrators(admin_account_id)

    accounts = [
        {"AccountId": account["Id"], "Email": account["Email"]}
        for account in organizations.list_accounts()
    ]

    args = ((admin_account_id, region, accounts) for region in regions)

    with ThreadPoolExecutor(max_workers=5) as executor:
        for _ in executor.map(lambda f: setup_region(*f), args):
            pass

    delegate_session = STS(management_session).assume_role(admin_account_id)

    # Aggregate Security Hub findings into primary region
    SecurityHub(delegate_session, primary_region).create_finding_aggregator()


@helper.create
@helper.update
def create(event: Dict[str, Any], context: LambdaContext) -> bool:
    logger.debug("Got Create or Update")
    setup_organization(primary_region=PRIMARY_REGION, regions=REGIONS)


@helper.delete
def delete(event: Dict[str, Any], context: LambdaContext) -> None:
    # Ignore deletion event
    return


@logger.inject_lambda_context(log_event=True)
def handler(event: Dict[str, Any], context: LambdaContext) -> None:
    # Set up a new landing zone
    if event.get("eventName") == "SetupLandingZone":
        primary_region = event["awsRegion"]
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

        return setup_organization(
            primary_region=primary_region,
            admin_account_id=admin_account_id,
            regions=REGIONS,
        )

    helper(event, context)
