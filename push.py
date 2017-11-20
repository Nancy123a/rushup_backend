import json
import logging
import boto3
import re

dynamo_db = boto3.resource('dynamodb')
client = boto3.client('sns')

table_name = "user_token"

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def save_token(event, context):

    print json.dumps(event,  encoding='ascii')

    # Parse the body as json object
    body = json.loads(event['body'])

    if 'token' not in body:
        logging.error("Validation Failed")
        raise Exception("Couldn't find token parameter.")
        return

    # Retrieve the phone number from path
    phone_number = event["requestContext"]["authorizer"]["claims"]["phone_number"]
    user_name = event["requestContext"]["authorizer"]["claims"]["cognito:username"]
    token = body["token"]

    registerWithSNS(phone_number, token)

    response = {
        "statusCode": 201,
        "body": json.dumps({})
    }

    return response


def publish_message(event, context):

    print json.dumps(event,  encoding='ascii')

    # Parse the body as json object
    body = json.loads(event['body'])

    if 'phone' not in body:
        logging.error("Validation Failed")
        raise Exception("Couldn't find phone parameter.")
        return

    if 'message' not in body:
        logging.error("Validation Failed")
        raise Exception("Couldn't find message parameter.")
        return

    phone = body["phone"]
    message = body["message"]

    endpointArn = retrieveEndpointArn(phone)

    if endpointArn == None:
        raise Exception("Sending Push to unregistered user")

    publish_response = client.publish(
        TargetArn=endpointArn,
        Message=message
    )


    response = {
        "statusCode": 200,
        "body": publish_response["MessageId"]
    }

    return response



def registerWithSNS(phone_number, token):

    endpointArn = retrieveEndpointArn(phone_number)

    updateNeeded = False
    createNeeded = (None == endpointArn)

    if createNeeded:
        # No platform endpoint ARN is stored; need to call createEndpoint. \
        endpointArn = createEndpoint(token, phone_number)
        createNeeded = False

    print("Retrieving platform endpoint data...")
    # Look up the platform endpoint and make sure the data in it is current, even if
    # it was just created.
    try:
        response = client.get_endpoint_attributes(EndpointArn=endpointArn)
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
        createEndpoint()

    print ("updateNeeded = " + updateNeeded)

    if updateNeeded:
        # The platform endpoint is out of sync with the current data;
        # update the token and enable it.
        print("Updating platform endpoint " + endpointArn)
        response = client.set_endpoint_attributes(
            EndpointArn=endpointArn,
            Attributes={
                'Token': token,
                'Enabled': "true"
            }
        )

# @return never null
def createEndpoint(token, phone_number):
    endpointArn = None
    try:
        print("Creating platform endpoint with token " + token)
        response = client.create_platform_endpoint(
            PlatformApplicationArn='arn:aws:sns:eu-west-1:261650959426:app/GCM/rush_up',
            Token=token,
            CustomUserData=phone_number
        )
        endpointArn = response["EndpointArn"]
    except Exception as ipe:
        message = ipe.getErrorMessage();
        print("Exception message: " + message)
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
    storeEndpointArn(phone_number, token, endpointArn)
    return endpointArn


# @return the ARN the app was registered under previously, or null if no
#        platform endpoint ARN is stored.
def retrieveEndpointArn(phone_number):

    key = {
        'phone': phone_number
    }

    result = dynamo_db.get_item(Key=key, ProjectionExpression="endpoint_arn", TableName=table_name)

    print json.dumps(result, encoding='ascii')

    if "endpoint_arn" in result:
        return result["endpoint_arn"]
    else:
        return None


#  Stores the platform endpoint ARN in permanent storage for lookup next time.
def storeEndpointArn(phone_number, token, endpoint_arn):

    item = {
        'phone': phone_number,
        'token': token,
        'endpoint_arn': endpoint_arn
    }

    print json.dumps(item,  encoding='ascii')

    dynamo_db.put_item(Item=item, TableName=table_name)
