import boto3
import botocore
import os
import sys

from jinjaform import log
from jinjaform.config import aws_provider, env, s3_backend, sessions


def backend_setup():

    region = s3_backend.get('region')
    if not region:
        return

    bucket = s3_backend.get('bucket')
    if bucket:

        log.ok('backend: s3://{} in {}', bucket, region)

        if sessions:
            s3_client = next(iter(sessions.values())).client('s3', region_name=region)
        else:
            s3_client = boto3.client('s3', region_name=region)

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

        if sessions:
            dynamodb_client = next(iter(sessions.values())).client('dynamodb', region_name=region)
        else:
            dynamodb_client = boto3.client('dynamodb', region_name=region)

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

    profile = aws_provider.get('profile')
    if not profile:
        return

    log.ok('aws-profile: {}', profile)

    botocore_session = botocore.session.Session(profile=profile)
    cli_cache_path = os.path.join(os.path.expanduser('~'), '.aws/cli/cache')
    cli_cache = botocore.credentials.JSONFileCache(cli_cache_path)
    botocore_session.get_component('credential_provider').get_provider('assume-role').cache = cli_cache
    session = boto3.Session(botocore_session=botocore_session)

    sessions[profile] = session

    try:
        creds = session.get_credentials().get_frozen_credentials()
    except KeyboardInterrupt:
        print()
        log.bad('aborted')
        sys.exit(1)

    env_vars = {
        'AWS_PROFILE': profile,
        'AWS_DEFAULT_PROFILE': profile,
        'AWS_ACCESS_KEY_ID': creds.access_key,
        'AWS_SECRET_ACCESS_KEY': creds.secret_key,
        'AWS_SESSION_TOKEN': creds.token,
    }
    for key, value in env_vars.items():
        if value:
            env[key] = value
