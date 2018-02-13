import boto3
import json
import os
import utility

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

def get_all_users_in_group(event,context):
    print json.dumps(event,  encoding='ascii')

    body= json.loads(event['body'])
    group_name=body['group_name']

    response = cognito.list_users_in_group(
        UserPoolId=os.environ["identityPoolId"],
        GroupName=group_name
    )

    list_of_user=[]

    if len(response["Users"]) > 0:
        users=response['Users']
        for user in users:
            list_of_user.append(user['Username'])

    data= {'user_list':list_of_user}

    print (json.dumps(data))

    response = {
        "statusCode": 201,
        "body":json.dumps(data)
    }
    return response