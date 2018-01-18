import boto3
import json
import uuid
import time
import user_push
import driver
import utility
import driver_push
import os
import random


stepfunctions = boto3.client('stepfunctions')
dynamo_db = boto3.resource('dynamodb', region_name='eu-west-1')

table = dynamo_db.Table('delivery')


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

    update_status(delivery_id, delivery_status)

    delivery = retrieve_delivery(delivery_id)

    if delivery_status == "accepted":
        user_push.push_message(delivery, delivery["from"], "delivery_update")
        step_input = dict()
        step_input["delivery"] = delivery

        step_response = stepfunctions.start_execution(
            stateMachineArn=os.environ['driverAssignState'],
            input=json.dumps(step_input)
        )
        print(step_response)
        #driver_push.push_to_nearby_message(delivery, "delivery_new")
    else:
        # We should only reach this when no driver is their
        user_push.push_message(delivery, delivery["to"], "delivery_update")
        user_push.push_message(delivery, delivery["from"], "delivery_update")

    response = {
        "statusCode": 200,
        "body": json.dumps({})
    }

    return response


def pick_up_dropoff_delivery(event, context):
    delivery_id = event["pathParameters"]["delivery_id"]
    delivery = retrieve_delivery(delivery_id)
    body = json.loads(event['body'])
    delivery_status = body["delivery_status"]
    code = body["code"]
    if delivery_status == "with_delivery" and delivery["from_code"] == code:
        update_status(delivery_id, delivery_status)
        user_push.push_message(delivery, delivery["to"], "delivery_update")
        user_push.push_message(delivery, delivery["from"], "delivery_update")
        response = {
            "statusCode": 200,
            "body": json.dumps({})
        }
        return response

    if delivery_status == "delivered" and delivery["to_code"] == code:
        update_status(delivery_id, delivery_status)
        user_push.push_message(delivery, delivery["to"], "delivery_update")
        user_push.push_message(delivery, delivery["from"], "delivery_update")
        driver.update_driver_status_internal(delivery["driver"]["identity_id"], "on")
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


# Method has to be called only by drivers
# to take over a delivery to be delivered
def assign_delivery(event, context):

    print json.dumps(event, encoding='ascii')
    delivery_id = event["pathParameters"]["delivery_id"]

    driver_id = event["requestContext"]["identity"]["cognitoIdentityId"]

    delivery_driver = driver.retrieve_driver(driver_id)

    delivery_status = 'assigned'

    key = {
        'id': delivery_id
    }

    table.update_item(
        Key=key,
        UpdateExpression='SET delivery_status = :v, driver = :d',
        ExpressionAttributeValues={
            ':v': delivery_status,
            ':d': delivery_driver,
            ':o': 'accepted'
        },
        ConditionExpression="delivery_status = :o"
    )

    driver.update_driver_status_internal(driver_id, "occupied")

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
        else:
            print('delivery has been accepted')
