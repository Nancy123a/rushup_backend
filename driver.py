import json
import boto3
import urllib
import os
import time
from boto3.dynamodb.conditions import Key, Attr
from geoindex import GeoGridIndex, GeoPoint


dynamo_db = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamo_db.Table('driver_token')
delivery_drivers_table = dynamo_db.Table('delivery_drivers')


def get_driver(event, context):

    print json.dumps(event, encoding='ascii')

    identity_id = urllib.unquote(event["pathParameters"]["driver_id"])

    driver = retrieve_driver(identity_id)

    response = {
        "statusCode": 201,
        "body": json.dumps(driver)
    }

    return response


def retrieve_driver(identity_id):

    result = table.get_item(
        Key={
            'identity_id': identity_id
        },
        ProjectionExpression="identity_id,phone,driver_location,username"
    )

    print json.dumps(result, encoding='ascii')

    if "Item" in result:
        return result["Item"]
    else:
        return None


def update_location(event, context):

    print json.dumps(event,  encoding='ascii')

    # Parse the body as json object
    body = json.loads(event['body'])

    identity_id = event["requestContext"]["identity"]["cognitoIdentityId"]

    table.update_item(
        Key={'identity_id':  identity_id},
        UpdateExpression='SET driver_location = :l',
        ExpressionAttributeValues={
            ':l': body
        }
    )

    response = {
        "statusCode": 200,
        "body": json.dumps({})
    }

    return response


def get_available_drivers(event, context):
    print json.dumps(event)
    delivery = event["delivery"]
    response = table.scan(
        FilterExpression=Attr('driver_status').eq('free')
    )

    drivers = []

    if "Items" in response:
        index = GeoGridIndex()
        for driver in response["Items"]:
            index.add_point(GeoPoint(float(driver["driver_location"]["latitude"]),float(driver["driver_location"]["longitude"]), ref=driver))

        center_point = GeoPoint(float(delivery["pickup_location"]["latitude"]), float(delivery["pickup_location"]["longitude"]))
        radius = int(os.environ["driverLookupRadius"])
        while not drivers:
            for point, distance in index.get_nearest_points(center_point, radius, 'km'):
                #print distance
                #print point
                #print json.dumps(point.ref)
                drivers.append(point.ref)
            print("We found {0} drivers for radius {1} km".format(len(drivers), radius))
            radius = radius * 2
        print drivers
        delivery_drivers_table.put_item(
            Item={
                "delivery_id": delivery["id"],
                "drivers": drivers,
                "ttl": int(time.time()) + (30 * 60)
            }
        )
        return drivers[0]
    else:
        return None