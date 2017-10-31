import json
import logging
import boto3
import uuid

dynamodb = boto3.resource('dynamodb')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def save_data(event, context):

    logger.info('got event{}'.format(event))

    # Parse the body as json object
    data = json.loads(event['body'])

    if 'token' not in data :
        logging.error("Validation Failed")
        raise Exception("Couldn't find token parameters.")
        return
    # Retrieve the phone number from path
    phoneNumber = event['pathParameters']['phoneNumber']

    body = {
        "phoneNumber": phoneNumber,
        "token": data['token']
    }

    # Check this example on how to save dynamodb https://github.com/serverless/examples/tree/master/aws-python-rest-api-with-dynamodb

    table = dynamodb.Table("rushup-mobilehub-1263655713-user-push")

    item = {
        'userId': str(uuid.uuid1()),
        'phone': int(phoneNumber),
        'token': data['token']
    }

    table.put_item(Item=item)

    logger.info('got body{}'.format(body))

    response = {
        "statusCode": 201,
        "body": json.dumps(item)
    }

    return response
