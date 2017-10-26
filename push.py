import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def saveData(event, context):

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

    logger.info('got body{}'.format(body))

    response = {
        "statusCode": 201,
        "body": json.dumps(body)
    }

    return response