import json
import user_push
import boto3
cognito = boto3.client('cognito-idp')

def get_all_group_of_users(event,context):

    print json.dumps(event,  encoding='ascii')

    user_name, phone_number = user_push.get_user(event["requestContext"]["identity"]["cognitoAuthenticationProvider"])

    print(user_name)

    list_of_groups=[]

    response = cognito.admin_list_groups_for_user(
        Username=user_name,
        UserPoolId='eu-west-1_w2rC3VeKI',
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

def get_all_users_in_group(event,context):

    print json.dumps(event,  encoding='ascii')

    user_name, phone_number = user_push.get_user(event["requestContext"]["identity"]["cognitoAuthenticationProvider"])

    response = cognito.list_users_in_group(
        UserPoolId='eu-west-1_w2rC3VeKI',
        GroupName=user_name
    )

    list_of_user=[]

    if len(response["Users"]) > 0:
        users=response['Users']
        for user in users:
            username=user['Username']
            list_of_user.append(username)

        data = dict()

        data['users_list'] = list_of_user

        if len(data) > 0:
            response = {
                "statusCode": 201,
                "body":json.dumps(data)
            }
        else:
            response = {
                "statusCode":400,
                "body":"no users found in this group"
            }
        return response