import json
import boto3
import os


dynamo_db = boto3.client('dynamodb')
cognito_sync = boto3.client('cognito-sync')
table_name = "user_token"


def sync(event, context):

    print json.dumps(event,  encoding='ascii')

    # Parse the body as json object
    contacts = json.loads(event['body'])

    if not isinstance(contacts, list):
        response = {
            "statusCode": 400,
            "body": "contacts is not in the request body or not a list"
        }
        return response

    result = []

    print("we received " + str(len(contacts)) + " contacts")

    for phone_number in contacts:
        # print (json.dumps(contact,  encoding='ascii'))
        user = check_phone(phone_number)
        if user is not None:
            if phone_number not in result:
                response = dict()
                response["phone_number"] = phone_number
                response["user_name"] = user["username"]
                response["locations"] = user["locations"]
                result.append(response)
    print(str(len(result)) + "/" + str(len(contacts)) + " are rushie contacts")

    response = {
        "statusCode": 200,
        "body": json.dumps(result)
    }

    return response


# @return Phone Number if it exist or None if it does not
def check_phone(phone_number):

    key = {
        'phone': {
            'S': phone_number
        }
    }

    result = dynamo_db.get_item(Key=key, ProjectionExpression="username,identity_id", TableName=table_name)

    # print json.dumps(result, encoding='ascii')

    if "Item" in result:
        user = dict()

        if 'username' in result["Item"]:
            user["username"] = result["Item"]["username"]["S"]
        else:
            user["username"] = 'unknown'

        if 'identity_id' in result["Item"]:
            user["locations"] = get_user_locations(result["Item"]["identity_id"]["S"])
        else:
            user["locations"] = []

        return user
    else:
        return None


def get_user_locations(identity_id):
    locations = []
    response = cognito_sync.list_records(
        IdentityPoolId=os.environ['identityPoolId'],
        IdentityId=identity_id,
        DatasetName=os.environ['locationDatasetName']
    )

    for record in response['Records']:
        location = dict()
        location['key'] = record['Key']
        location['value'] = record['Value']
        locations.append(location)

    return locations
