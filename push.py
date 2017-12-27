import json
import logging
import boto3
import re
import os

dynamo_db = boto3.client('dynamodb')
cognito = boto3.client('cognito-idp')
sns = boto3.client('sns')

table_name = "user_token"

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def save_token(event, context):

    print json.dumps(event,  encoding='ascii')

    # Parse the body as json object
    body = json.loads(event['body'])

    user_name, phone_number = get_user(event["requestContext"]["identity"]["cognitoAuthenticationProvider"])

    identity_id = event["requestContext"]["identity"]["cognitoIdentityId"]

    if user_name is None:
        raise "Unable to extract user from security Provider"

    if 'token' not in body:
        logging.error("Validation Failed")
        response = {
            "statusCode": 400,
            "body": "token field is not in the request body"
        }
        return response

    # user_name = event["requestContext"]["authorizer"]["claims"]["cognito:username"]
    token = body["token"]

    registerWithSNS(phone_number, user_name, token, identity_id)

    response = {
        "statusCode": 201,
        "body": json.dumps({})
    }

    return response


def publish_message(event, context):

    print(json.dumps(event,  encoding='ascii'))

    # Parse the body as json object
    body = json.loads(event['body'])

    if 'phone' not in body:
        logging.error("Validation Failed")
        response = {
            "statusCode": 400,
            "body": "Phone field is not in the request body"
        }
        return response

    if 'message' not in body:
        logging.error("Validation Failed")
        response = {
            "statusCode": 400,
            "body": "message field is not in the request body"
        }
        return response

    phone = body["phone"]
    message = dict()
    message["message"] = body["message"]
    if 'type' not in body:
        message["type"] = "delivery"
    else:
        message["type"] = body["type"]
        message["message_type"] = body["type"]
    data = dict()
    data["data"] = message
    gcm = dict()
    gcm["GCM"] = json.dumps(data)

    print(json.dumps(gcm,  encoding='ascii'))

    endpointArn = retrieveEndpointArn(phone)

    if endpointArn is None:
        response = {
            "statusCode": 404,
            "body": "Sending push to unknown user, not Rushie"
        }
        return response

    publish_response = sns.publish(
        TargetArn=endpointArn,
        Message=json.dumps(gcm),
        MessageStructure="json"
    )


    response = {
        "statusCode": 200,
        "body": publish_response["MessageId"]
    }

    return response


def registerWithSNS(phone_number, user_name, token, identity_id):

    endpointArn = retrieveEndpointArn(phone_number)

    updateNeeded = False
    createNeeded = False
    
    if endpointArn is None:
        createNeeded = True

    if createNeeded:
        # No platform endpoint ARN is stored; need to call createEndpoint.
        print("New Phone number creating Endpoint")
        endpointArn = createEndpoint(phone_number, user_name, token, identity_id)
        createNeeded = False

    print("Retrieving platform endpoint data...")
    # Look up the platform endpoint and make sure the data in it is current, even if
    # it was just created.
    try:
        response = sns.get_endpoint_attributes(EndpointArn=endpointArn)
        attributes = response["Attributes"]
        if attributes["Token"] != token:
            updateNeeded = True
        if attributes["Enabled"] != "true":
            updateNeeded = True

    except Exception as exception:
        # We had a stored ARN, but the platform endpoint associated with it
        # disappeared. Recreate it.
        createNeeded = True

    if createNeeded:
        createEndpoint(phone_number, user_name, token, identity_id)

    print("updateNeeded = " + str(updateNeeded))

    if updateNeeded:
        # The platform endpoint is out of sync with the current data;
        # update the token and enable it.
        print("Updating platform endpoint " + endpointArn)
        response = sns.set_endpoint_attributes(
            EndpointArn=endpointArn,
            Attributes={
                'Token': token,
                'Enabled': "true"
            }
        )


# @return never null
def createEndpoint(phone_number, user_name, token, identity_id):
    endpointArn = None
    try:
        print("Creating platform endpoint with token " + token)
        response = sns.create_platform_endpoint(
            PlatformApplicationArn=os.environ['androidPlatformApplicationArn'],
            Token=token,
            CustomUserData=phone_number
        )
        endpointArn = response["EndpointArn"]
    except Exception as ipe:
        message = ipe
        print(message)
        m = re.search(".*Endpoint (arn:aws:sns[^ ]+) already exists with the same token.*", message)
        if m is not None:
            # The platform endpoint already exists for this token, but with
            # additional custom data that
            # createEndpoint doesn't want to overwrite. Just use the
            # existing platform endpoint.
            endpointArn = m.group(1)
        else:
            # Rethrow the exception, the input is actually bad.
            raise ipe
    storeEndpointArn(phone_number, user_name, token, identity_id, endpointArn)
    return endpointArn


# @return the ARN the app was registered under previously, or null if no
#        platform endpoint ARN is stored.
def retrieveEndpointArn(phone_number):

    key = {
        'phone': {
            'S': phone_number
        }
    }

    result = dynamo_db.get_item(Key=key, ProjectionExpression="endpoint_arn", TableName=table_name)

    print json.dumps(result, encoding='ascii')

    if "Item" in result:
        return result["Item"]["endpoint_arn"]["S"]
    else:
        return None


#  Stores the platform endpoint ARN in permanent storage for lookup next time.
def storeEndpointArn(phone_number, user_name, token, identity_id, endpoint_arn):

    item = {
        'phone': {
            'S': phone_number
        },
        'endpoint_arn':  {
            'S': endpoint_arn
        },
        'username': {
            'S': user_name
        },
        'identity_id': {
            'S': identity_id
        },
        'token': {
            'S': token
        }
    }

    print json.dumps(item,  encoding='ascii')

    dynamo_db.put_item(Item=item, TableName=table_name)


# Get User from security context.
# May return null if user not found
def get_user(cognitoAuthenticationProvider):

    # cognito-idp.eu-west-2.amazonaws.com/eu-west-2_9Rfg3SRNy,cognito-idp.eu-west-2.amazonaws.com/eu-west-2_9Rfg3SRNy:CognitoSignIn:4b586b11-0e4d-4690-b30f-0b50ce31beda
    m = re.search(".*/(.+):CognitoSignIn:(.+)", cognitoAuthenticationProvider)
    if m is not None:
        userPoolId = m.group(1)
        sub = m.group(2)
    else:
        # Rethrow the exception, the input is actually bad.
        raise "Unable to extract user from security Provider"

    print("userPoolId" + userPoolId)

    cognito_filter = "sub='" + sub + "'"

    print("filter  " + cognito_filter)

    response = cognito.list_users(
        UserPoolId=userPoolId,
        AttributesToGet=["phone_number"],
        Limit=1,
        Filter=cognito_filter
    )
    if len(response["Users"]) > 0:
        user = response["Users"][0]
        # This is the default phone_number
        phone_number = None
        for attribute in user["Attributes"]:
            if attribute["Name"] == "phone_number":
                phone_number = attribute["Value"]
        if phone_number is None:
            return None, None
        return user["Username"], phone_number
    else:
        return None, None
