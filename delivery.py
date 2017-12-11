import boto3
import json

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

table = dynamodb.Table('delivery')

def save_delivery(event, context):

    print json.dumps(event,  encoding='ascii')

    delivery = json.loads(event['body'], object_hook=Delivery)

    # print(delivery.from)
    print(delivery.to)


class Delivery:
    def __init__(self, json):
        vars(self).update(json)
