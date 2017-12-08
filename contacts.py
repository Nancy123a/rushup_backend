import json
import boto3

dynamo_db = boto3.client('dynamodb')

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
        user_name = check_phone(contact["phone"])
        if user_name is not None:
            if contact["contact_id"] not in result:
                response = dict()
                response["contact_id"] = contact["contact_id"]
                response["user_name"] = user_name
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
        return result["Item"]["username"]["S"]
    else:
        return None
