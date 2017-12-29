import json
import boto3

dynamo_db = boto3.client('dynamodb')
cognito = boto3.client('cognito-idp')

table_name = 'driver_token'


def update_location(event, context):

    print json.dumps(event,  encoding='ascii')

    # Parse the body as json object
    body = json.loads(event['body'])

    identity_id = event["requestContext"]["identity"]["cognitoIdentityId"]

    dynamo_db.update_item(
        TableName=table_name,
        Key={
            'identity_id': {
                'S': identity_id
            }
        },
        AttributeUpdates={
            'location': {
                'M': {
                    'latitude': {'N': body["latitude"]},
                    'longitude': {'N': body["longitude"]}
                }
            }
        }
    )

    response = {
        "statusCode": 201,
        "body": json.dumps({})
    }

    return response
