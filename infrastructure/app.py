#!/usr/bin/env python3
from aws_cdk import core as cdk
from stacks.smokler_stack import SmoklerStack

app = cdk.App()
SmoklerStack(app, 'smokler')

app.synth()
