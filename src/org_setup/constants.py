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

from typing import Set

from botocore.config import Config

__all__ = [
    "AI_OPT_OUT_POLICY_NAME",
    "AI_OPT_OUT_POLICY",
    "BOTO3_CONFIG",
    "ORGANIZATION_ANALYZER_NAME",
    "MANAGEMENT_ANALYZER_NAME",
    "SERVICE_ACCESS_PRINCIPALS",
    "DELEGATED_ADMINISTRATOR_PRINCIPALS",
]

BOTO3_CONFIG = Config(
    retries={
        "max_attempts": 10,
        "mode": "standard",
    }
)

AI_OPT_OUT_POLICY_NAME: str = "AllOptOutPolicy"

# https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_ai-opt-out_syntax.html#ai-opt-out-policy-examples
AI_OPT_OUT_POLICY = {
    "services": {
        "@@operators_allowed_for_child_policies": ["@@none"],
        "default": {
            "@@operators_allowed_for_child_policies": ["@@none"],
            "opt_out_policy": {
                "@@operators_allowed_for_child_policies": ["@@none"],
                "@@assign": "optOut",
            },
        },
    }
}

ORGANIZATION_ANALYZER_NAME: str = "OrganizationAnalyzer"

MANAGEMENT_ANALYZER_NAME: str = "ManagementAnalyzer"

SERVICE_ACCESS_PRINCIPALS: Set[str] = frozenset(
    {
        "backup.amazonaws.com",
        "config.amazonaws.com",
        "config-multiaccountsetup.amazonaws.com",
        "detective.amazonaws.com",
        "guardduty.amazonaws.com",
        "inspector2.amazonaws.com",
        "malware-protection.guardduty.amazonaws.com",
        "securitylake.amazonaws.com",
        "securityhub.amazonaws.com",
        "macie.amazonaws.com",
    }
)

DELEGATED_ADMINISTRATOR_PRINCIPALS: Set[str] = frozenset(
    {
        "access-analyzer.amazonaws.com",
        "config-multiaccountsetup.amazonaws.com",
        "detective.amazonaws.com",
        "guardduty.amazonaws.com",
        "inspector2.amazonaws.com",
        "securitylake.amazonaws.com",
        "securityhub.amazonaws.com",
        "macie.amazonaws.com",
        "storage-lens.s3.amazonaws.com",
    }
)
