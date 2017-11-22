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

    for contact_id, phone_number in contacts.iteritems():
        # print (str(contact_id) + str(phone_number))
        user = check_phone(phone_number)
        if user is not None:
            result.insert(0, contact_id)
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

    result = dynamo_db.get_item(Key=key, ProjectionExpression="phone", TableName=table_name)

    # print json.dumps(result, encoding='ascii')

    if "Item" in result:
        return result["Item"]["phone"]["S"]
    else:
        return None
