import json
import boto3
import urllib

dynamo_db = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamo_db.Table('driver_token')


def get_driver(event, context):

    print json.dumps(event, encoding='ascii')

    identity_id = urllib.unquote(event["pathParameters"]["driver_id"])

    driver = retrieve_driver(identity_id)

    response = {
        "statusCode": 201,
        "body": json.dumps(driver)
    }

    return response


def retrieve_driver(identity_id):

    result = table.get_item(
        Key={
            'identity_id': identity_id
        },
        ProjectionExpression="identity_id,phone,driver_location,username"
    )

    print json.dumps(result, encoding='ascii')

    if "Item" in result:
        return result["Item"]
    else:
        return None


def update_location(event, context):

    print json.dumps(event,  encoding='ascii')

    # Parse the body as json object
    body = json.loads(event['body'])

    identity_id = event["requestContext"]["identity"]["cognitoIdentityId"]

    table.update_item(
        Key={'identity_id':  identity_id},
        UpdateExpression='SET driver_location = :l',
        ExpressionAttributeValues={
            ':l': body
        }
    )

    response = {
        "statusCode": 200,
        "body": json.dumps({})
    }

    return response
