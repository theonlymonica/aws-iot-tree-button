#!/usr/bin/env python3

import aws_cdk as cdk
import yaml

from greengadget.greengadget_stack import GreengadgetStack


app = cdk.App()
with open("config.yaml", 'r') as stream:
    try:
        config = yaml.safe_load(stream)
        GreengadgetStack(app, "greengadget", config=config)
    except yaml.YAMLError as exc:
        print(exc)

app.synth()
