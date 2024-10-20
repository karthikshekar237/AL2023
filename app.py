#!/usr/bin/env python3
import os
import boto3
import sys
import time
from configparser import ConfigParser

import aws_cdk as cdk

from al2023arm.al2023arm_stack import Al2023ArmStack
from pygit2 import Repository


app=cdk.App()
branch = app.node.try_get_context("branch")
workspace=app.node.try_get_context("workspace")
branch=str(branch).replace("_","-")
print(workspace)

config = ConfigParser()
config.read('config.ini')
conf_dict = {}
variables = config.items(workspace)

conf_dict = {key: value for key, calue in variables}

stackname = conf_dict.get('stackname')

if stackname == None:
    print("The stack name is not configured!")
    sys.exit(1)

stackname = str(stackname) + branch
Al2023ArmStack(app, stackname, branch=branch,workspace=workspace, env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')))