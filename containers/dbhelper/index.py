import sys
import cfnresponse
import psycopg2
import boto3
from os import getenv
import logging
import traceback
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    print(event)
    if event['RequestType'] == 'Delete':
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        sys.exit(0)
    logger.info(getenv("AWS_DEFAULT_REGION"))
    ssm = boto3.client('ssm', region_name=getenv('AWS_DEFAULT_REGION'))
    try:
        # EVENT PARAMETERS
        db_name = event['ResourceProperties']['RDSUri']['DbName']
        db_host = event['ResourceProperties']['RDSUri']['Address']
        db_port = event['ResourceProperties']['RDSUri']['Port']
        logical_resource_id = event['LogicalResourceId']
        # SSM PARAMETERS
        master_user = ssm.get_parameter(Name='/airflow/postgres/masteruser')['Parameter']['Value']
        master_password = ssm.get_parameter(Name='/airflow/postgres/masterpassword', WithDecryption=True)['Parameter']['Value']
        airflow_user = ssm.get_parameter(Name='/airflow/postgres/userairflow')['Parameter']['Value']
        airflow_password = ssm.get_parameter(Name='/airflow/postgres/passwordairflow', WithDecryption=True)['Parameter']['Value']
        logger.info("Creating user with data %s" % (airflow_user))

        client = psycopg2.connect(dbname=db_name, user=master_user, password=master_password, host=db_host, port=db_port)
        cursor = client.cursor()
        cursor.execute("CREATE USER %s WITH PASSWORD '%s'" % (airflow_user, airflow_password))
        cursor.execute("GRANT ALL ON DATABASE %s TO %s" % (db_name, airflow_user))
        cursor.execute("GRANT ALL ON SCHEMA public TO %s" % (airflow_user))
        logger.info("User created successfully")
        client.commit()
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, logical_resource_id)
        sys.exit(0)
    except Exception as e :
        exception_type, exception_value, exception_traceback = sys.exc_info()
        traceback_string = traceback.format_exception(exception_type, exception_value, exception_traceback)
        err_msg = json.dumps({
            "errorType": exception_type.__name__,
            "errorMessage": str(exception_value),
            "stackTrace": traceback_string
        })
        logger.error(err_msg)
        cfnresponse.send(event, context, cfnresponse.FAILED, {})