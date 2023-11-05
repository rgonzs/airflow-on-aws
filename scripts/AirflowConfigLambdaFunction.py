import cfnresponse
import boto3
import io
import sys, logging, traceback, json

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info(event)
    if event['RequestType'] == 'Delete':
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        return
    s3 = boto3.client('s3', region_name='${AWS::Region}')
    ssm = boto3.client('ssm', region_name='${AWS::Region}')
    
    try:
        config = io.BytesIO()
        #  AIRFLOW CONFIG VERSION ID
        config_version = event['ResourceProperties']['Airflow']['ConfigVersion']

        # POSTGRES CONFIG
        postgres_password = ssm.get_parameter(Name=event['ResourceProperties']['RDSUri']['Password'], WithDecryption=True)['Parameter']['Value']
        postgres_user = event['ResourceProperties']['RDSUri']['User']
        postgres_address = event['ResourceProperties']['RDSUri']['Address']
        postgres_port = event['ResourceProperties']['RDSUri']['Port']
        postgres_db = event['ResourceProperties']['RDSUri']['DbName']
        rds_uri = f'postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_address}:{postgres_port}/{postgres_db}'
        # REDIS CONFIG
        redis_password = ssm.get_parameter(Name=event['ResourceProperties']['RedisUri']['Password'], WithDecryption=True)['Parameter']['Value']
        redis_port = event['ResourceProperties']['RedisUri']['Port']
        redis_address = event['ResourceProperties']['RedisUri']['Address']
        redis_uri = f'redis://:{redis_password}@{redis_address}:{redis_port}/0'
        # AIRFLOW SECRETS
        fernet_key = ssm.get_parameter(Name=event['ResourceProperties']['Airflow']['FernetKey'], WithDecryption=True)['Parameter']['Value']
        secret_key = ssm.get_parameter(Name=event['ResourceProperties']['Airflow']['SecretKey'], WithDecryption=True)['Parameter']['Value']
        # DOWNLOAD CONFIG TEMPLATE
        s3.download_fileobj(
            Bucket = event['ResourceProperties']['BucketName'],
            Key = 'config-templates/airflow.cfg',
            Fileobj = config,
            ExtraArgs = {'VersionId': config_version}
        )
        template = config.getvalue().decode('utf-8')
        template = template.replace('#{FERNET_KEY}', fernet_key)
        template = template.replace('#{SECRET_KEY}', secret_key)
        template = template.replace('#{POSTGRES_URI}', rds_uri)
        template = template.replace('#{REDIS_URI}', redis_uri)
        s3.upload_fileobj(
            Bucket = event['ResourceProperties']['BucketName'],
            Key = 'config/airflow.cfg',
            Fileobj = io.BytesIO(str.encode(template, encoding='utf-8'))
        )
        response_data = {}
        response_data['BucketName'] = event['ResourceProperties']['BucketName']
        cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data, "AirflowConfigCreator")
    except Exception:
        cfnresponse.send(event, context, cfnresponse.FAILED, {})
        exception_type, exception_value, exception_traceback = sys.exc_info()
        traceback_string = traceback.format_exception(exception_type, exception_value, exception_traceback)
        err_msg = json.dumps({
            "errorType": exception_type.__name__,
            "errorMessage": str(exception_value),
            "stackTrace": traceback_string
        })
        logger.error(err_msg)