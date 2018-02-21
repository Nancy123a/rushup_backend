import boto3
import json
import os

import driver_push
import user_push
import utility

cognito = boto3.client('cognito-idp')

def create_group(event,context):

    print json.dumps(event,  encoding='ascii')
    user_name= event["userName"]
    type=event["request"]["userAttributes"]["custom:type"]
    userPoolId=os.environ["identityPoolId"]

    print(type)

    if type is "company":
     cognito.create_group(
     GroupName=user_name,
     UserPoolId=userPoolId,
     Description="Company group"
     )

    return event


def check_if_company(event,context):

    print json.dumps(event, encoding='ascii')
    type=event['requestContext']['authorizer']['claims']['custom:type']

    response = {
        "statusCode": 201,
        "headers" : { "Access-Control-Allow-Origin" : "*" },  # Required for CORS support to work
        "body": json.dumps(type)
    }
    return response

def assign_user(event,context):

    print json.dumps(event,  encoding='ascii')

    body= json.loads(event['body'])
    email=body['email']
    group_name=body['group_name']

    print ("group name "+group_name)

    addUser = cognito.admin_add_user_to_group(
        UserPoolId=os.environ["identityPoolId"],
        Username=email,
        GroupName=group_name
    )

    response = {
        "statusCode": 201,
        "headers" : { "Access-Control-Allow-Origin" : "*" },  # Required for CORS support to work
        "body": json.dumps({})
    }
    return response

def delete_user(event,context):
    print json.dumps(event,  encoding='ascii')

    body= json.loads(event['body'])
    email=body['email']
    group_name=body['group_name']

    response = cognito.admin_remove_user_from_group(
        UserPoolId=os.environ["identityPoolId"],
        Username=email,
        GroupName=group_name
    )

    response = {
        "statusCode": 201,
        "headers" : { "Access-Control-Allow-Origin" : "*" },  # Required for CORS support to work
        "body": json.dumps({})
    }
    return response



def get_all_users_in_group(event,context):
    print json.dumps(event,  encoding='ascii')

    user_name, phone_number = user_push.get_user(event["requestContext"]["identity"]["cognitoAuthenticationProvider"])

    response = cognito.list_users_in_group(
        UserPoolId=os.environ["identityPoolId"],
        GroupName=user_name
    )

    list_of_user=[]

    if len(response["Users"]) > 0:
        users=response['Users']
        for user in users:
            list_of_user.append(user['Username'])

    data= dict()

    data['users_list'] = list_of_user

    print (json.dumps(data))

    response = {
        "statusCode": 201,
        "body":json.dumps(data)
    }
    return response

def get_all_users_in_group_cognito(event,context):

    print json.dumps(event,  encoding='ascii')

    group_name=event['requestContext']['authorizer']['claims']['name']

    response = cognito.list_users_in_group(
    UserPoolId=os.environ["identityPoolId"],
    GroupName=group_name
    )

    list_of_user=[]

    if len(response["Users"]) > 0:
     users=response['Users']
     for user in users:
         username=user['Username']
         phone=user['Attributes'][4]['Value']
         email=user['Attributes'][7]['Value']
         _user=username+","+phone+","+email
         list_of_user.append(_user)

         data = dict()

         data['users_list'] = list_of_user

         print (json.dumps(data))

         response = {
         "statusCode": 201,
         "headers" : { "Access-Control-Allow-Origin" : "*" },  # Required for CORS support to work
          "body":json.dumps(data)
         }
         return response

def get_all_group_of_users(event,context):

    print json.dumps(event,  encoding='ascii')

    user_name, phone_number = user_push.get_user(event["requestContext"]["identity"]["cognitoAuthenticationProvider"])

    print(user_name)

    list_of_groups=[]

    response = cognito.admin_list_groups_for_user(
        Username=user_name,
        UserPoolId=os.environ["identityPoolId"],
    )

    if len(response["Groups"])>0:
        for key in response['Groups']:
            list_of_groups.append(key['GroupName'])

    data = dict()

    data['groups_list'] = list_of_groups

    print (json.dumps(data))
    response = {
        "statusCode": 201,
        "body":json.dumps(data)
    }

    return response
