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




def assign_user(event,context):

    print json.dumps(event,  encoding='ascii')
    body= json.loads(event['body'])
    username=body['username']
    group_name=body['group_name']

    print ("group name "+group_name)

    addUser = cognito.admin_add_user_to_group(
        UserPoolId=os.environ["identityPoolId"],
        Username=username,
        GroupName=group_name
    )

    response = {
        "statusCode": 201,
        "body": "{}"
    }
    return response

def delete_user(event,context):
    print json.dumps(event,  encoding='ascii')

    body= json.loads(event['body'])
    username=body['username']
    group_name=body['group_name']

    response = cognito.admin_remove_user_from_group(
        UserPoolId=os.environ["identityPoolId"],
        Username=username,
        GroupName=group_name
    )

    response = {
        "statusCode": 201,
        "body": "{}"
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
