import boto3
client = boto3.client('stepfunctions')


def lambda_handler(event, context):
    # TODO implement
    # Your code goes here
    #This line starts the execution of the stateMachine
    response = client.start_execution(
    stateMachineArn='The ARN of your state machine',
    #name='string',
    #The input here determines how many seconds the stateMachine stays in the "wait" task
    input='{"time": 1}'
    )
    print(response)
    return "done"
