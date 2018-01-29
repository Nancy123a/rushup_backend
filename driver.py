import json
import boto3
import urllib
import os
import time
from boto3.dynamodb.conditions import Key, Attr
from geoindex import GeoGridIndex, GeoPoint
import delivery
from user_push import push_message
import utility


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


def get_delivery_drivers(event, context):

    print json.dumps(event, encoding='ascii')

    delivery_id = urllib.unquote(event["pathParameters"]["delivery_id"])

    result = delivery_drivers_table.get_item(
        Key={
            'delivery_id': delivery_id
        },
        ProjectionExpression="drivers"
    )

    locations = []

    result = utility.replace_decimals(result)

    print json.dumps(result, encoding='ascii')

    if "Item" in result:
        if "drivers" in result["Item"]:
            for driver in result["Item"]["drivers"]:
                print json.dumps(driver, encoding='ascii')
                locations.append(driver["driver_location"])

    response = {
        "statusCode": 200,
        "body": json.dumps(locations)
    }

    return response


def update_driver_status(event, context):

    print json.dumps(event,  encoding='ascii')

    # Parse the body as json object
    body = json.loads(event['body'])

    if "status" not in body:
        print("Unable to extract status from body")
        response = {
            "statusCode": 500,
            "body": "Unable to extract status"
        }
        return response

    status = body["status"]

    if status == "on" or status == "off":

        identity_id = event["requestContext"]["identity"]["cognitoIdentityId"]

        update_driver_status_internal(identity_id, body["status"])

        response = {
            "statusCode": 200,
            "body": json.dumps({})
        }

        return response

    else:
        print("Invalid Status")
        response = {
            "statusCode": 500,
            "body": "Invalid Status"
        }
        return response


def update_driver_status_internal(identity_id, status, delivery_id=None, successful_delivery=False):

    expression_attribute_values = dict()
    expression_attribute_values[":s"] = status

    update_expression = 'SET driver_status = :s'

    if successful_delivery:
        update_expression = update_expression + ' , delivery_count = delivery_count + :c'
        expression_attribute_values[":c"] = 1

    if delivery_id:
        update_expression = update_expression + ', delivery_id = :d'
        expression_attribute_values[":d"] = delivery_id
    else:
        update_expression = update_expression + ' REMOVE delivery_id'

    print update_expression

    table.update_item(
        Key={'identity_id':  identity_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values
    )


def retrieve_driver(identity_id):

    result = table.get_item(
        Key={
            'identity_id': identity_id
        },
        ProjectionExpression="identity_id,phone,driver_location,username,delivery_count"
    )

    result = utility.replace_decimals(result)

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

    result = table.update_item(
        Key={'identity_id':  identity_id},
        UpdateExpression='SET driver_location = :l',
        ExpressionAttributeValues={
            ':l': body
        },
        ReturnValues="ALL_NEW"
    )

    driver = result["Attributes"]

    driver = utility.replace_decimals(driver)

    print json.dumps(driver, encoding='ascii')

    if "delivery_id" in driver:
        if driver["delivery_id"] != "":
            dlv = delivery.retrieve_delivery(driver["delivery_id"])
            print json.dumps(dlv, encoding='ascii')
            d = 1000
            if dlv["delivery_status"] == "assigned":
                point1 = GeoPoint(float(dlv["pickup_location"]["latitude"]), float(dlv["pickup_location"]["longitude"]))
                point2 = GeoPoint(float(driver["driver_location"]["latitude"]), float(driver["driver_location"]["longitude"]))
                d = point1.distance_to(point2)
                print "Distance between driver and pickup {} KM".format(d)
                if d < 0.5:
                    push_message(dlv, dlv["from"], "driver_knock")
            if dlv["delivery_status"] == "with_delivery":
                point1 = GeoPoint(float(dlv["dropoff_location"]["latitude"]), float(dlv["dropoff_location"]["longitude"]))
                point2 = GeoPoint(float(driver["driver_location"]["latitude"]), float(driver["driver_location"]["longitude"]))
                d = point1.distance_to(point2)
                print "Distance between driver and dropoff {} KM".format(d)
                if d < 0.5:
                    msg = dict()
                    msg["message"] = "knock knock"
                    push_message(dlv, dlv["to"], "driver_knock")

    response = {
        "statusCode": 200,
        "body": json.dumps({})
    }

    return response


def get_available_drivers(event, context):
    print json.dumps(event)
    dlv = event["delivery"]
    if "drivers" in event:
        if "result" in event["drivers"]:
            selected_drivers = event["drivers"]["result"]
        else:
            selected_drivers = []
    else:
        selected_drivers = []
    response = table.scan(
        FilterExpression=Attr('driver_status').eq('on')
    )

    drivers = []

    if "Items" in response:
        index = GeoGridIndex()
        for driver in response["Items"]:
            index.add_point(GeoPoint(float(driver["driver_location"]["latitude"]),float(driver["driver_location"]["longitude"]), ref=driver))

        center_point = GeoPoint(float(dlv["pickup_location"]["latitude"]), float(dlv["pickup_location"]["longitude"]))
        radius = int(os.environ["driverMinLookupRadius"])
        max_radius = int(os.environ["driverMaxLookupRadius"])
        while not drivers:
            print "Searching for drivers in {} km radius".format(radius)
            for point, distance in index.get_nearest_points(center_point, radius, 'km'):
                i = 0
                driver = point.ref
                while i < len(selected_drivers):
                    print str(i)
                    print selected_drivers[i]
                    print driver
                    if selected_drivers[i]["identity_id"] == driver["identity_id"]:
                        print "Delivery already proposed to Driver {} in previous attempt".format(driver["identity_id"])
                        driver = None
                        break
                    i = i + 1
                if driver:
                    drivers.append(driver)
            print("We found {0} drivers for radius {1} km".format(len(drivers), radius))
            radius = radius * 2
            if radius >= max_radius:
                print("Radius is more than 40 KM stop searching")
                break
        print drivers
        delivery_drivers_table.put_item(
            Item={
                "delivery_id": dlv["id"],
                "drivers": drivers,
                "ttl": int(time.time()) + (30 * 60)
            }
        )
        if len(drivers) > 0:
            selected_drivers.insert(0, drivers[0])
        else:
            selected_drivers = []
    else:
        selected_drivers = []

    return_item = dict()
    return_item["result"] = selected_drivers
    return_item["driver_count"] = len(selected_drivers)
    return return_item
