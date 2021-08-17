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

logger = Logger(child=True)

__all__ = ["FMS"]


class FMS:
    def __init__(self, session: boto3.Session) -> None:
        self.client = session.client("fms")

    def associate_admin_account(self, account_id: str) -> None:
        logger.info(
            f"Enabling account {account_id} to be Firewall Manager admin account"
        )
        try:
            self.client.associate_admin_account(AdminAccount=account_id)
            logger.debug(
                f"Enabled account {account_id} to be Firewall Manager admin account"
            )
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] != "InternalErrorException":
                logger.exception(
                    f"Unable to enable account {account_id} to be Firewall Manager admin account"
                )
                raise error
