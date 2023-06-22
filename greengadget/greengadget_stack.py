import subprocess
from pathlib import Path
from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    RemovalPolicy,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_lambda_python_alpha as _lambda_alpha,
    aws_iot as iot,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_ssm as ssm,
    aws_sns as sns,
    aws_secretsmanager as secretsmanager,
)


class GreengadgetStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_list = config['project_list']
        url = config['url']
        gadgeter_id = config['gadgeter_id']
        token = config['token']
        certificateInfo = config['certificateInfo']
        mqtt_topic = config['mqtt_topic']

        sns_topic = sns.Topic(
            self, "GreengadgetSNSTopic",
            display_name="Greengadget SNS Topic",
        )

        lambda_role = iam.Role(
            self, "GreengadgetLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSIoTFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSNSFullAccess"),
            ],
        )

        ssm_parameter = ssm.StringParameter(
            self, "GreengadgetSSMParameter",
            parameter_name="/greengadget/token",
            string_value=token,
            description="Token for the Greengadget API",
            tier=ssm.ParameterTier.STANDARD,
        )

        # Creates a new IAM user, access and secret keys, and stores the secret access key in a Secret.
        user = iam.User(self, "QRCodeUser")
        access_key = iam.AccessKey(self, "AccessKey", user=user)
        secret = secretsmanager.Secret(self, "Secret",
                                       secret_string_value=access_key.secret_access_key
                                       )

        s3_bucket = s3.Bucket(
            self, "GreengadgetS3Bucket",
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        user_policy = iam.Policy(
            self, "GreengadgetUserPolicy",
            policy_name="GreengadgetUserPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:List*",
                        "s3:Get*"
                    ],
                    resources=[
                        s3_bucket.bucket_arn + "/*",
                    ],
                ),
            ],
        )

        user.attach_inline_policy(user_policy)

        dynamodb_table = dynamodb.Table(
            self, "GreengadgetDynamoDBTable",
            partition_key=dynamodb.Attribute(
                name="ID",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        iot_printer = iot.CfnThing(
            self, "GreengadgetIoTPrinter",
            thing_name="printer",
        )

        path = Path("printer.csr")
        if not path.is_file():
            self.generate_csr(certificateInfo, "printer.csr")

        with open("printer.csr", "r") as csr_file:
            printer_csr = csr_file.read()

        iot_printer_certificate = iot.CfnCertificate(
            self, "GreengadgetIoTPrinterCertificate",
            status="ACTIVE",
            certificate_signing_request=printer_csr
        )

        iot_printer_principal_attachment = iot.CfnThingPrincipalAttachment(
            self, "GreengadgetIoTPrinterPrincipalAttachment",
            thing_name=iot_printer.thing_name,
            principal=iot_printer_certificate.attr_arn,
        )

        iot_printer_policy = iot.CfnPolicy(
            self, "GreengadgetIoTPrinterPolicy",
            policy_document={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "iot:*",
                        "Resource": "*",
                    },
                ],
            },
            policy_name="printer",
        )

        iot_printer_policy_attachment = iot.CfnPolicyPrincipalAttachment(
            self, "GreengadgetIoTPrinterPolicyAttachment",
            policy_name=iot_printer_policy.policy_name,
            principal=iot_printer_certificate.attr_arn
        )

        iot_button = iot.CfnThing(
            self, "GreengadgetIoTButton",
            thing_name="button",
        )

        path = Path("button.csr")
        if not path.is_file():
            self.generate_csr(certificateInfo, "button.csr")

        with open("button.csr", "r") as csr_file:
            button_cert = csr_file.read()

        iot_button_certificate = iot.CfnCertificate(
            self, "GreengadgetIoTButtonCertificate",
            status="ACTIVE",
            certificate_signing_request=button_cert
        )

        iot_button_principal_attachment = iot.CfnThingPrincipalAttachment(
            self, "GreengadgetIoTButtonPrincipalAttachment",
            thing_name=iot_button.thing_name,
            principal=iot_button_certificate.attr_arn,
        )

        iot_button_policy = iot.CfnPolicy(
            self, "GreengadgetIoTButtonPolicy",
            policy_document={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "iot:*",
                        "Resource": "*",
                    },
                ],
            },
            policy_name="button",
        )

        iot_button_policy_attachment = iot.CfnPolicyPrincipalAttachment(
            self, "GreengadgetIoTButtonPolicyAttachment",
            policy_name=iot_button_policy.policy_name,
            principal=iot_button_certificate.attr_arn
        )

        lambda_function = _lambda_alpha.PythonFunction(
            self, "GreengadgetLambdaFunction",
            runtime=_lambda.Runtime.PYTHON_3_10,
            entry="src/lambda",
            index="lambda_function.py",
            handler="lambda_handler",
            architecture=_lambda.Architecture.X86_64,
            memory_size=256,
            role=lambda_role,
            timeout=Duration.seconds(60),
            environment={
                "BUCKET": s3_bucket.bucket_name,
                "TABLE": dynamodb_table.table_name,
                "PROJECT_LIST": ",".join(project_list),
                "SSM_PARAMETER": ssm_parameter.parameter_name,
                "URL": url,
                "PLANTER_ID": gadgeter_id,
                "TARGET": iot_printer.attr_arn,
                "SNS_TOPIC": sns_topic.topic_arn,
            },
        )

        iot_button_thing_topic_rule = iot.CfnTopicRule(
            self, "GreengadgetIoTButtonThingTopic",
            topic_rule_payload=iot.CfnTopicRule.TopicRulePayloadProperty(
                sql="SELECT * FROM '" + mqtt_topic + "'",
                actions=[
                    iot.CfnTopicRule.ActionProperty(
                        lambda_=iot.CfnTopicRule.LambdaActionProperty(
                            function_arn=lambda_function.function_arn,
                        ),
                    ),
                ],
            ),
        )

        # add permissions to invoke lambda function from iot
        lambda_function.add_permission(
            "GreengadgetLambdaFunctionPermission",
            principal=iam.ServicePrincipal("iot.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=iot_button_thing_topic_rule.attr_arn,
        )

    def generate_csr(self, certificateInfo, fileName):
        # -nodes - private key should not be encrypted with a passphrase
        subprocess.run(
            ["openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", fileName + "_private.key", "-out", fileName, "-subj",
             certificateInfo])
