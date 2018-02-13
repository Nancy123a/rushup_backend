import boto3
import json
import os

cognito = boto3.client('cognito-idp')

def save(event,context):

    print json.dumps(event,  encoding='ascii')
    body = json.loads(event['body'])
    group_name =body['group_name']
    userPoolId=os.environ["identityPoolId"]

    group = cognito.create_group(
    GroupName=group_name,
    UserPoolId=userPoolId,
    Description="Company group"
    )
    print(group)
    response = {
    "statusCode": 201,
    "body": "{}"
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
        "body": "{}"
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
        "body": "{}"
    }
    return response