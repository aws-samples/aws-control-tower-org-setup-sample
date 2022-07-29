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
from typing import List, Dict

import boto3

AWS_PROFILE = "root-admin"


def get_current_account(session: boto3.Session) -> str:
    client = session.client("sts")
    return client.get_caller_identity()["Account"]


def get_accounts(session: boto3.Session) -> List[str]:
    client = session.client("organizations")
    account_ids = []
    paginator = client.get_paginator("list_accounts")
    page_iterator = paginator.paginate(PaginationConfig={"PageSize": 10})
    for page in page_iterator:
        for account in page.get("Accounts", []):
            if account["Status"] == "ACTIVE":
                account_ids.append(account["Id"])
    return account_ids


def get_regions(session: boto3.Session) -> List[str]:
    client = session.client("ec2")
    response = client.describe_regions(
        Filters=[
            {
                "Name": "opt-in-status",
                "Values": [
                    "opt-in-not-required",
                ],
            },
        ],
        AllRegions=False,
    )
    regions = [region["RegionName"] for region in response.get("Regions", [])]
    return regions


def assume_role(session: boto3.Session, account_id: str) -> Dict[str, str]:
    role_arn = f"arn:aws:iam::{account_id}:role/AWSControlTowerExecution"
    client = session.client("sts")
    response = client.assume_role(RoleArn=role_arn, RoleSessionName="disable_security_hub")
    credentials = response["Credentials"]
    return credentials


def disable_security_hub(
    account_id: str, region: str, credentials: Dict[str, str] = None, session: boto3.Session = None
):
    if credentials:
        assumed_session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
    elif session:
        assumed_session = session
    else:
        return

    client = assumed_session.client("securityhub", region_name=region)

    standard_subscription_arns = []

    paginator = client.get_paginator("get_enabled_standards")
    page_iterator = paginator.paginate(PaginationConfig={"MaxItems": 100})
    for page in page_iterator:
        for standard in page.get("StandardsSubscriptions", []):
            standard_subscription_arns.append(standard["StandardsSubscriptionArn"])

    if not standard_subscription_arns:
        print(f"No enabled Security Hub standards found in {account_id} {region}")
        return

    client.batch_disable_standards(StandardsSubscriptionArns=standard_subscription_arns)

    print(f"Disabled {len(standard_subscription_arns)} standards in {account_id} {region}")


def main():
    session = boto3.Session(profile_name=AWS_PROFILE)

    current_account_id = get_current_account(session)
    account_ids = get_accounts(session)
    regions = get_regions(session)

    print(f"Disabling security hub in {len(account_ids)} accounts and {len(regions)}")

    for account_id in account_ids:
        if account_id == current_account_id:
            args = ((account_id, region, None, session) for region in regions)
            with ThreadPoolExecutor(max_workers=10) as executor:
                for _ in executor.map(lambda f: disable_security_hub(*f), args):
                    pass
        else:
            credentials = assume_role(session, account_id)

            args = ((account_id, region, credentials) for region in regions)
            with ThreadPoolExecutor(max_workers=10) as executor:
                for _ in executor.map(lambda f: disable_security_hub(*f), args):
                    pass


if __name__ == "__main__":
    main()
