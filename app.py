#!/usr/bin/env python3
import os
import boto3
import sys
import time
from configparser import ConfigParser

import aws_cdk as cdk

from al2023arm.al2023arm_stack import Al2023ArmStack
# Assuming there will be a similar stack for x86 in `al2023x86`
from al2023x86.al2023x86_stack import Al2023X86Stack
from pygit2 import Repository


app = cdk.App()
branch = app.node.try_get_context("branch")
workspace = app.node.try_get_context("workspace")
branch = str(branch).replace("_", "-")
print(workspace)

config = ConfigParser()
config.read('config.ini')
conf_dict = {}
variables = config.items(workspace)

# Load config values into dictionary
conf_dict = {key: value for key, value in variables}

stackname = conf_dict.get('stackname')

if stackname is None:
    print("The stack name is not configured!")
    sys.exit(1)

stackname = str(stackname) + branch
platform = conf_dict.get('instance_types')

# Determine if we're building for ARM or x86
if "t4g" in platform:  # ARM-based instance type (ARM architecture)
    print(f"Creating ARM-based AMI using stack: {stackname}")
    Al2023ArmStack(app, stackname, branch=branch, workspace=workspace, env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
        region=os.getenv('CDK_DEFAULT_REGION')))
    
elif "t2" in platform:  # x86-based instance type (x86 architecture)
    print(f"Creating x86-based AMI using stack: {stackname}")
    Al2023X86Stack(app, stackname, branch=branch, workspace=workspace, env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
        region=os.getenv('CDK_DEFAULT_REGION')))
else:
    print(f"Unsupported platform type for AMI creation: {platform}")
    sys.exit(1)

app.synth()
