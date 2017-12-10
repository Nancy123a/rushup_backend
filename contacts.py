import json
import boto3
import os

dynamo_db = boto3.client('dynamodb')
cognito_sync = boto3.client('cognito-sync')
table_name = "user_token"


def sync(event, context):

    print json.dumps(event,  encoding='ascii')

    # Parse the body as json object
    body = json.loads(event['body'])

    if 'contacts' not in body:
        response = {
            "statusCode": 400,
            "body": "contacts is not in the request body"
        }
        return response

    contacts = body["contacts"]
    result = []

    print("we received " + str(len(contacts)) + " contacts")

    for contact in contacts:
        # print (json.dumps(contact,  encoding='ascii'))
        user = check_phone(contact["phone"])
        if user is not None:
            if contact["contact_id"] not in result:
                response = dict()
                response["contact_id"] = contact["contact_id"]
                response["user_name"] = user["username"]
                response["locations"] = user["locations"]
                result.append(response)
    print(str(len(result)) + "/" + str(len(contacts)) + " are rushie contacts")
    body = {
        "contacts": result
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response


# @return Phone Number if it exist or None if it does not
def check_phone(phone_number):

    key = {
        'phone': {
            'S': phone_number
        }
    }

    result = dynamo_db.get_item(Key=key, ProjectionExpression="username", TableName=table_name)

    # print json.dumps(result, encoding='ascii')

    if "Item" in result:
        user = dict()
        user["username"] = result["Item"]["username"]["S"]
        user["locations"] = get_user_locations(result["Item"]["identity_id"]["S"])
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
        locations.append(json.dumps(location))

    return locations