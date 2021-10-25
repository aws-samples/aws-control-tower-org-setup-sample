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

from typing import List

from aws_lambda_powertools import Logger
import boto3

logger = Logger(child=True)

__all__ = ["EC2"]


class EC2:
    def __init__(self, session: boto3.Session, region: str) -> None:
        self.client = session.client("ec2", region_name=region)

    def get_all_regions(self) -> List[str]:
        """
        Return all regions that don't require opt-in
        """
        regions = [
            region["RegionName"]
            for region in self.client.describe_regions(
                Filters=[{"Name": "opt-in-status", "Values": ["opt-in-not-required"]}],
                AllRegions=False,
            )["Regions"]
        ]
        return sorted(regions)
