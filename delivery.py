import boto3
import json
import uuid
import time
import user_push
import driver
import utility
import driver_push

dynamo_db = boto3.resource('dynamodb', region_name='eu-west-1')

table = dynamo_db.Table('delivery')


def save_delivery(event, context):

    print json.dumps(event,  encoding='ascii')

    delivery = json.loads(event['body'])

    if "id"  not in delivery:
        delivery["id"] = str(uuid.uuid1())
        delivery["delivery_status"] = "pending"
        delivery["delivery_date"] = int(time.time())

    table.put_item(
        Item=delivery
    )

    # print(delivery.from)
    print(delivery)

    user_push.push_message(delivery, delivery["to"], "delivery_request")

    response = {
        "statusCode": 201,
        "body": json.dumps(delivery)
    }

    return response


def update_delivery_status(event, context):

    print json.dumps(event,  encoding='ascii')

    delivery_id = event["pathParameters"]["delivery_id"]

    body = json.loads(event['body'])

    delivery_status = body["delivery_status"]

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

    delivery = retrieve_delivery(delivery_id)

    delivery['delivery_status'] = delivery_status

    if delivery_status == "accepted":
        user_push.push_message(delivery, delivery["from"], "delivery_update")
        driver_push.push_to_nearby_message(delivery, "delivery_new")
    else:
        user_push.push_message(delivery, delivery["to"], "delivery_update")
        user_push.push_message(delivery, delivery["from"], "delivery_update")

    response = {
        "statusCode": 200,
        "body": json.dumps({})
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
