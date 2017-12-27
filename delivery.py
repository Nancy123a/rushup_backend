import boto3
import json
import uuid

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

table = dynamodb.Table('delivery')

def save_delivery(event, context):

    print json.dumps(event,  encoding='ascii')

    delivery = json.loads(event['body'])

    if "id"  not in delivery:
        delivery["id"] = str(uuid.uuid1())

    table.put_item(
        Item=delivery
    )

    # print(delivery.from)
    print(delivery)


class Delivery:
    def __init__(self, json):
        vars(self).update(json)
