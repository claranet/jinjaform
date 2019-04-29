import boto_source_profile_mfa
import boto3
import sys
import threading

from functools import lru_cache

from jinjaform import log
from jinjaform.config import env


aws_provider = {}
s3_backend = {}

lock = threading.Lock()


@lru_cache()
def _get_session(**kwargs):
    if 'profile_name' in kwargs:
        return boto_source_profile_mfa.get_session(**kwargs)
    else:
        return boto3.Session(**kwargs)


def get_default_session():
    session_kwargs = {}
    if aws_provider:
        terraform_boto_session_map = {
            'access_key': 'aws_access_key_id',
            'secret_key': 'aws_secret_access_key',
            'token': 'aws_session_token',
            'profile': 'profile_name',
            'region': 'region_name',
        }
        for terraform_key, boto_key in terraform_boto_session_map.items():
            value = aws_provider.get(terraform_key)
            if value:
                session_kwargs[boto_key] = value
    return get_session(**session_kwargs)


def get_session(**kwargs):
    with lock:
        return _get_session(**kwargs)


def backend_setup():

    region = s3_backend.get('region')
    if not region:
        return

    bucket = s3_backend.get('bucket')
    if bucket:

        log.ok('backend: s3://{} in {}', bucket, region)

        s3_client = get_default_session().client('s3')

        try:
            response = s3_client.get_bucket_versioning(
                Bucket=bucket
            )
        except s3_client.exceptions.NoSuchBucket:
            bucket_exists = False
            bucket_versioning = False
        else:
            bucket_exists = True
            bucket_versioning = response['Status'] == 'Enabled'

        if not bucket_exists:

            if not log.accept('backend: create s3://{} in {}', bucket, region):
                log.bad('backend: bucket not created')
                sys.exit(1)

            log.ok('backend: creating bucket')
            s3_client.create_bucket(
                ACL='private',
                Bucket=bucket,
                CreateBucketConfiguration={
                    'LocationConstraint': region,
                },
            )
            s3_client.get_waiter('bucket_exists').wait(Bucket=bucket)

        if not bucket_versioning:
            log.ok('backend: enabling versioning')
            s3_client.put_bucket_versioning(
                Bucket=bucket,
                VersioningConfiguration={
                    'Status': 'Enabled',
                },
            )

    dynamodb_table = s3_backend.get('dynamodb_table')
    if dynamodb_table:

        log.ok('backend: dynamodb://{} in {}', dynamodb_table, region)

        dynamodb_client = get_default_session().client('dynamodb')

        try:
            dynamodb_client.describe_table(
                TableName=dynamodb_table,
            )
        except dynamodb_client.exceptions.ResourceNotFoundException:

            if not log.accept('backend: create dynamodb://{} in {}', dynamodb_table, region):
                log.bad('backend: table not created')
                sys.exit(1)

            log.ok('creating table')
            dynamodb_client.create_table(
                TableName=dynamodb_table,
                AttributeDefinitions=[
                    {
                        'AttributeName': 'LockID',
                        'AttributeType': 'S',
                    }
                ],
                KeySchema=[
                    {
                        'AttributeName': 'LockID',
                        'KeyType': 'HASH',
                    },
                ],
                BillingMode='PAY_PER_REQUEST',
            )


def credentials_setup():
    """
    Sets up AWS credentials using Terraform AWS provider blocks.
    """

    if not aws_provider:
        return

    session = get_default_session()

    try:
        creds = session.get_credentials().get_frozen_credentials()
    except KeyboardInterrupt:
        print()
        log.bad('aborted')
        sys.exit(1)

    env_vars = {
        'AWS_ACCESS_KEY_ID': creds.access_key,
        'AWS_SECRET_ACCESS_KEY': creds.secret_key,
        'AWS_SESSION_TOKEN': creds.token,
    }
    for key, value in env_vars.items():
        if value:
            env[key] = value
