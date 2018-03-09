import boto3
import json
import uuid
import time
import user_push
import driver
import utility
import os
import random
from boto3.dynamodb.conditions import Key, Attr


stepfunctions = boto3.client('stepfunctions')
dynamo_db = boto3.resource('dynamodb', region_name='eu-west-1')

table = dynamo_db.Table('delivery')
driver_token_table=dynamo_db.Table('driver_token')

def save_delivery(event, context):

    print json.dumps(event,  encoding='ascii')

    delivery = json.loads(event['body'])

    if "id" not in delivery:
        delivery["id"] = str(uuid.uuid1())
        delivery["delivery_status"] = "pending"
        delivery["delivery_date"] = int(time.time())
        delivery["from_code"] = str(random.randrange(1001, 9999, 1))
        delivery["to_code"] = str(random.randrange(1001, 9999, 1))
    table.put_item(
        Item=delivery
    )

    # print(delivery.from)
    print(delivery)

    user_push.push_message(delivery, delivery["to"], "delivery_request")

    step_input = dict()
    step_input["time"] = int(os.environ["deliveryTimeout"])
    step_input["delivery_id"] = delivery["id"]

    step_response = stepfunctions.start_execution(
        stateMachineArn=os.environ['deliveryTimeoutStep'],
        input=json.dumps(step_input)
    )

    print(step_response)

    response = {
        "statusCode": 201,
        "body": json.dumps(delivery)
    }

    return response


def update_delivery_status(event, context):

    print json.dumps(event,  encoding='ascii')

    if "pathParameters" in event:
        delivery_id = event["pathParameters"]["delivery_id"]
        body = json.loads(event['body'])
        delivery_status = body["delivery_status"]
    else:
        delivery_id = event["delivery"]["id"]
        if event["drivers"]["driver_count"] == 0:
            delivery_status = "no_driver"
        else:
            # we should never reach this
            delivery_status = "unknown"

    if delivery_status in ["accepted", "rejected", "no_driver"]:

        update_status(delivery_id, delivery_status)

        delivery = retrieve_delivery(delivery_id)

        if delivery_status == "accepted":
            user_push.push_message(delivery, delivery["from"], "delivery_update")
            if delivery["from"] != delivery["identity_id"]:
                user_push.push_message(delivery, delivery["identity_id"], "delivery_update")
            step_input = dict()
            step_input["delivery"] = delivery

            step_response = stepfunctions.start_execution(
                stateMachineArn=os.environ['driverAssignState'],
                input=json.dumps(step_input)
            )
            print(step_response)
        else:
            # We should only reach this when no driver is their
            user_push.push_message(delivery, delivery["to"], "delivery_update")
            user_push.push_message(delivery, delivery["from"], "delivery_update")
            if delivery_status != "no_driver":
                if delivery["from"] != delivery["identity_id"]:
                    user_push.push_message(delivery, delivery["identity_id"], "delivery_update")

        response = {
            "statusCode": 200,
            "body": json.dumps({})
        }
        return response

    else:
        response = {
            "statusCode": 500,
            "body": "Invalid status"
        }
        return response


def pick_up_dropoff_delivery(event, context):
    print json.dumps(event,  encoding='ascii')
    delivery_id = event["pathParameters"]["delivery_id"]
    delivery = retrieve_delivery(delivery_id)
    body = json.loads(event['body'])
    delivery_status = body["delivery_status"]
    code = body["code"]
    if delivery_status == "with_delivery" and delivery["from_code"] == code:
        update_status(delivery_id, delivery_status)
        delivery["delivery_status"] = "with_delivery"
        delivery = retrieve_delivery(delivery_id)
        user_push.push_message(delivery, delivery["to"], "delivery_update")
        user_push.push_message(delivery, delivery["from"], "delivery_update")
        response = {
            "statusCode": 200,
            "body": json.dumps({})
        }
        return response

    if delivery_status == "delivered" and delivery["to_code"] == code:
        update_status(delivery_id, delivery_status)
        delivery["delivery_status"] = "delivered"
        user_push.push_message(delivery, delivery["to"], "delivery_update")
        user_push.push_message(delivery, delivery["from"], "delivery_update")
        driver.update_driver_status_internal(delivery["driver"]["identity_id"], "on", None, True)
        response = {
            "statusCode": 200,
            "body": json.dumps({})
        }
        return response

    print("Wrong Code or invalid status")
    response = {
        "statusCode": 500,
        "body": "Wrong Code or invalid status"
    }
    return response


def get_delivery(event, context):

    print json.dumps(event,  encoding='ascii')
    delivery_id = event["pathParameters"]["delivery_id"]

    delivery = retrieve_delivery(delivery_id)

    response = {
        "statusCode": 200,
        "body": json.dumps(delivery)
    }

    return response


def get_delivery_state(event, context):
    delivery_id = event["delivery"]["id"]
    return retrieve_delivery(delivery_id)


def knock_monitor(event, context):
    step_input = dict()
    step_input["delivery"] = event["delivery"]
    step_input["driver"] = event["drivers"]["result"][0]
    step_response = stepfunctions.start_execution(
        stateMachineArn=os.environ['driverAssignState'],
        input=json.dumps(step_input)
    )
    print(step_response)
    return




def get_distance(event, context):
    origin = event["origin"]
    destination = event["destination"]
    to = event["to"]
    d = distance(origin, destination)
    msg = dict()
    msg["message"] = "knock knock"
    if d < 0.5:
        user_push.push_message(msg, to, "driver_knock")
        return True
    else:
        return False

def get_history(event,context):
    print json.dumps(event)
        #cognito-idp.eu-west-1.amazonaws.com/eu-west-1_w2rC3VeKI,cognito-idp.eu-west-1.amazonaws.com/eu-west-1_w2rC3VeKI:CognitoSignIn:9e3de258-a135-4753-b46d-0e16874098a4
    user_name, phone_number = user_push.get_user(event["requestContext"]["identity"]["cognitoAuthenticationProvider"])

    body = json.loads(event['body'])

    delivery_date=body['delivery_date']

    print (phone_number)

    if user_name is None:
        print("Unable to extract user from security Provider")
        response = {
            "statusCode": 500,
            "body": "Error while getting user"
        }
        return response

    identity_id_history = table.query(
        IndexName='identity_id-delivery_date-index',
        ScanIndexForward= False,
        KeyConditionExpression=Key('identity_id').eq(phone_number) & Key('delivery_date').gt(delivery_date),
        Limit= 20
       )

    identity_id_history_array=identity_id_history['Items']

    data= dict()

    data['identity_history'] = identity_id_history_array

    print (json.dumps(data,cls=utility.DecimalEncoder))

    response = {
        "statusCode": 201,
        "body":json.dumps(data,cls=utility.DecimalEncoder)
    }
    return response

def get_promotion(event,context):
    user_name, phone_number = user_push.get_user(event["requestContext"]["identity"]["cognitoAuthenticationProvider"])

    print (phone_number)

    if user_name is None:
        print("Unable to extract user from security Provider")
        response = {
            "statusCode": 500,
            "body": "Error while getting user"
        }
        return response

    from_promotion = table.query(
        IndexName='from-delivery_status-index',
        ScanIndexForward= False,
        KeyConditionExpression=Key('from').eq(phone_number) & Key('delivery_status').eq('delivered')
    )

    to_promotion = table.query(
        IndexName='to-delivery_status-index',
        ScanIndexForward= False,
        KeyConditionExpression=Key('to').eq(phone_number) & Key('delivery_status').eq('delivered')
    )

    from_promotion_array=from_promotion['Items']

    to_promotion_array=to_promotion['Items']


    data= {'from_delivered':from_promotion_array,'to_delivered':to_promotion_array}

    print (json.dumps(data,cls=utility.DecimalEncoder))

    response = {
    "statusCode": 201,
    "body":json.dumps(data,cls=utility.DecimalEncoder)
    }

    return response


def clear_history(event,context):
    print json.dumps(event)

    user_name, phone_number = user_push.get_user(event["requestContext"]["identity"]["cognitoAuthenticationProvider"])

    print (phone_number)

    table.delete_item(
        Key={
            'identity_id': phone_number
        }
    )

    response = {
        "statusCode": 201,
        "body": json.dumps({})
    }

    return response

def get_driver_history(event,context):

    print json.dumps(event)

    identity_id=event["requestContext"]["identity"]["cognitoIdentityId"]

    body = json.loads(event['body'])

    delivery_date=body['delivery_date']

    print (identity_id)

    if identity_id is None:
        print("Unable to extract user from security Provider")
        response = {
            "statusCode": 500,
            "body": "Error while gettng driver id"
        }
        return response

    driver_id_history = table.query(
        IndexName='driver_id-delivery_date-index',
        ScanIndexForward= False,
        KeyConditionExpression=Key('driver_id').eq(identity_id) & Key('delivery_date').gt(delivery_date),
        Limit= 20
    )

    print (driver_id_history)

    driver_id_history_array=driver_id_history['Items']

    data= {'driver_history':driver_id_history_array}

    print (json.dumps(data,cls=utility.DecimalEncoder))

    response = {
        "statusCode": 201,
        "body":json.dumps(data,cls=utility.DecimalEncoder)
    }
    return response

def get_driver_balance(event,context):
    print json.dumps(event)

    identity_id=event["requestContext"]["identity"]["cognitoIdentityId"]

    print (identity_id)

    if identity_id is None:
       print("Unable to extract user from security Provider")
       response = {
        "statusCode": 500,
        "body": "Error while getting driver id"
       }
       return response

    driver_id_balance = table.query(
        IndexName='driver_id-delivery_status-index',
        ScanIndexForward= False,
        KeyConditionExpression=Key('driver_id').eq(identity_id) & Key('delivery_status').eq("delivered")
     )

    print (driver_id_balance)

    driver_id_balance_array=driver_id_balance['Items']

    data= {'driver_balance':driver_id_balance_array}

    print (json.dumps(data,cls=utility.DecimalEncoder))

    response = {
        "statusCode": 201,
        "body":json.dumps(data,cls=utility.DecimalEncoder)
    }
    return response


# Method has to be called only by drivers
# to take over a delivery to be delivered
def assign_delivery(event, context):

    print json.dumps(event, encoding='ascii')
    delivery_id = event["pathParameters"]["delivery_id"]

    driver_id = event["requestContext"]["identity"]["cognitoIdentityId"]

    delivery_driver = driver.retrieve_driver(driver_id)

    print(json.dumps(delivery_driver))

    delivery_status = 'assigned'

    key = {
        'id': delivery_id
    }

    table.update_item(
        Key=key,
        UpdateExpression='SET delivery_status = :v, driver = :d, driver_id = :di',
        ExpressionAttributeValues={
            ':v': delivery_status,
            ':d': delivery_driver,
            ':di': driver_id,
            ':o': 'accepted'
        },
        ConditionExpression="delivery_status = :o"
    )

    driver.update_driver_status_internal(driver_id, "occupied", delivery_id)

    delivery = retrieve_delivery(delivery_id)

    user_push.push_message(delivery, delivery["to"], "delivery_update")
    user_push.push_message(delivery, delivery["from"], "delivery_update")

    response = {
        "statusCode": 200,
        "body": json.dumps({})
    }

    return response


def retrieve_delivery(delivery_id):

    key = {
        'id': delivery_id
    }

    result = table.get_item(Key=key)

    result = utility.replace_decimals(result)

    print json.dumps(result, encoding='ascii')

    if "Item" in result:
        return result["Item"]
    else:
        return None


def update_status(delivery_id, delivery_status):
    key = {
        'id': delivery_id
    }
    # we should add condition that item exist before trying to update
    table.update_item(
        Key=key,
        UpdateExpression='SET delivery_status = :v',
        ExpressionAttributeValues={
            ':v': delivery_status
        }
    )


def check_if_delivery_timeout(event, context):

    print json.dumps(event,  encoding='ascii')

    delivery_id = event["delivery_id"]

    delivery = retrieve_delivery(delivery_id)

    if delivery:
        if delivery['delivery_status'] == 'pending':
            print('delivery is still pending , timing out')
            update_status(delivery_id, 'timeout')
            delivery = retrieve_delivery(delivery_id)
            user_push.push_message(delivery, delivery["to"], "delivery_update")
            user_push.push_message(delivery, delivery["from"], "delivery_update")
            if delivery["from"] != delivery["identity_id"]:
                user_push.push_message(delivery, delivery["identity_id"], "delivery_update")
        else:
            print('delivery has been accepted')
