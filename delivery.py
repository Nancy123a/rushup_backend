import boto3
import json
import uuid
import time
import push

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

table = dynamodb.Table('delivery')

def save_delivery(event, context):

    print json.dumps(event,  encoding='ascii')

    delivery = json.loads(event['body'])

    if "id"  not in delivery:
        delivery["id"] = str(uuid.uuid1())
        delivery["status"] = "pending"
        delivery["delivery_date"] = int(time.time())

    table.put_item(
        Item=delivery
    )

    # print(delivery.from)
    print(delivery)

    push_request = dict()
    push_request["message"] = delivery
    push_request["type"] = "delivery_request"
    push_request["phone"] = delivery["to"]

    body = dict()
    body["body"] = json.dumps(push_request)

    push.publish_message(body, context)

    response = {
        "statusCode": 201,
        "body": json.dumps(delivery)
    }

    return response


def update_delivery_status(event, context):

    print json.dumps(event,  encoding='ascii')

    delivery_id = event["pathParameters"]["delivery_id"]

    body = json.loads(event['body'])

    status = body["status"]

    key = {
        'id': delivery_id
    }

    table.update_item(
        Key=key,
        UpdateExpression='SET status = :val1',
        ExpressionAttributeValues={
            'val1': status
        }
    )

    response = {
        "statusCode": 200,
        "body": json.dumps({})
    }

    return response


def retrieveDelivery(delivery_id):

    key = {
        'id': delivery_id
    }

    result = table.get_item(Key=key)

    print json.dumps(result, encoding='ascii')

    if "Item" in result:
        return result["Item"]
    else:
        return None
