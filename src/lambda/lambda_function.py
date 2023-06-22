import json
import qrcode
import datetime
import boto3
import os
import logging
import random
import string
import requests
import time

logger = logging.getLogger()
logger.setLevel(os.getenv('LOGLEVEL', 'DEBUG').upper())

s3 = boto3.resource('s3')
dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')
sns = boto3.client('sns')
iot = boto3.client('iot')

table = dynamodb.Table(os.getenv('TABLE'))
bucket = os.getenv('BUCKET')
ssm_parameter_name = os.getenv('SSM_PARAMETER')
url = os.getenv('URL')
planter_id = os.getenv('PLANTER_ID')
target = os.getenv('TARGET')
region = os.environ['AWS_REGION']
sns_topic = os.getenv('SNS_TOPIC')
project_list = os.getenv('PROJECT_LIST').split(",")


def lambda_handler(event, context):
    logger.debug("Received event: " + json.dumps(event, indent=2))
    # get the token from ssm parameter
    try:
        ssm_parameter = ssm.get_parameter(Name=ssm_parameter_name, WithDecryption=True)
        token = ssm_parameter['Parameter']['Value']
        logger.debug("Token: " + token)
        # if the token is empty, return an error
        if token == "":
            logger.error("Token is empty")
            # try to send an SNS message
            try:
                sns.publish(
                    TopicArn=sns_topic,
                    Message="Token is empty",
                    Subject="GreenPlaNTT Error"
                )
            except Exception as e:
                logger.error("Error sending SNS message: " + str(e))
            return {
                'statusCode': 500,
                'body': json.dumps("Token is empty")
            }
    except Exception as e:
        logger.error("Error getting SSM parameter: " + str(e))
        # try to send an SNS message
        try:
            sns.publish(
                TopicArn=sns_topic,
                Message="Error getting SSM parameter: " + str(e),
                Subject="GreenPlaNTT Error"
            )
        except Exception as e:
            logger.error("Error sending SNS message: " + str(e))
        return {
            'statusCode': 500,
            'body': json.dumps("Error getting SSM parameter: " + str(e))
        }
    # generate a random ID of 16 chars for the image name
    imageid = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

    # call the API to create the tree, retrying while the json.loads(response.text)['status'] is not ok, wait 3 seconds between retries
    while True:
        try:
            project = random.choice(project_list)
            logger.debug("Project: " + project)
            payload = json.dumps({
                "recipients": [
                    {
                        "internal_id": imageid
                    }
                ],
                "planter_id": planter_id,
                "species_id": project,
                "quantity": 1,
                "message": "Grazie per la tua visita! NTT DATA ha piantato per te questo albero"
            })
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            logger.debug("Response: " + response.text)
            # if the response is not ok, return an error
            if response.status_code != 200:
                logger.error("Error calling API: " + response.text)
                # try to send an SNS message
                try:
                    sns.publish(
                        TopicArn=sns_topic,
                        Message="Error calling API: " + response.text,
                        Subject="GreenPlaNTT Error"
                    )
                except Exception as e:
                    logger.error("Error sending SNS message: " + str(e))
                return {
                    'statusCode': 500,
                    'body': json.dumps("Error calling API: " + response.text)
                }

            if json.loads(response.text)['status'] == "ok":
                logger.debug("Tree created")
                # get the collect_url from the response
                collect_url = json.loads(response.text)['trees'][0]['collect_url']
                treenation_id = json.loads(response.text)['trees'][0]['id']
                payment_id = json.loads(response.text)['payment_id']
                logger.debug("Collect URL: " + collect_url)
                # if the tree is created, exit the loop
                break
            else:
                # if the tree is not created, wait 3 seconds and retry
                logger.debug("Tree not created, retrying")
                time.sleep(3)
        except Exception as e:
            logger.error("Error calling API: " + str(e))
            return {
                'statusCode': 500,
                'body': json.dumps("Error calling API: " + str(e))
            }

    # generate a timestamp for the image name
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    input_data = collect_url
    # Creating an instance of qrcode
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=2)
    qr.add_data(input_data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    filepath = "/tmp/" + imageid + ".png"
    # save the image with timestamp in the name
    img.save(filepath)

    # Upload the image to S3
    try:
        s3.Bucket(bucket).upload_file(filepath, imageid + ".png")
        logger.debug("Uploaded to S3")
    except Exception as e:
        logger.error("Error uploading to S3: " + str(e))
        # try to send an SNS message
        try:
            sns.publish(
                TopicArn=sns_topic,
                Message="Error uploading to S3: " + str(e),
                Subject="GreenPlaNTT Error"
            )
        except Exception as e:
            logger.error("Error sending SNS message: " + str(e))
        return {
            'statusCode': 500,
            'body': json.dumps("Error uploading to S3: " + str(e))
        }

    # create an AWS IoT job with RunCommand as template
    try:
        iot.create_job(
            jobId='RunCommand-' + imageid,
            targets=[target],
            jobTemplateArn='arn:aws:iot:' + region + '::jobtemplate/AWS-Run-Command:1.0',
            documentParameters={
                'command': "/root/stampa.sh,s3://" + bucket + "/" + imageid + ".png"
            }
        )
        logger.debug("Created AWS IoT job")
    except Exception as e:
        logger.error("Error creating AWS IoT job: " + str(e))
        return {
            'statusCode': 500,
            'body': json.dumps("Error creating AWS IoT job: " + str(e))
        }

    # save the image S3 URL in DynamoDB with a random ID
    try:
        table.put_item(
            Item={
                'ID': imageid,
                'treenation_id': treenation_id,
                'payment_id': payment_id,
                'timestamp': timestamp,
                'URL': "https://" + bucket + ".s3.amazonaws.com/" + imageid + ".png"
            }
        )
        logger.debug("Saved to DynamoDB")
    except Exception as e:
        logger.error("Error saving to DynamoDB: " + str(e))
        # try to send an SNS message
        try:
            sns.publish(
                TopicArn=sns_topic,
                Message="Error saving to DynamoDB: " + str(e),
                Subject="GreenPlaNTT Error"
            )
        except Exception as e:
            logger.error("Error sending SNS message: " + str(e))
        return {
            'statusCode': 500,
            'body': json.dumps("Error saving to DynamoDB: " + str(e))
        }

    return {
        'statusCode': 200,
        'body': json.dumps({"message": "Done"})
    }
