import os
import boto3
from botocore.client import Config

B2_ENDPOINT = os.getenv("s3.eu-central-003.backblazeb2.com")
B2_KEY = os.getenv("f69accbc6328")
B2_SECRET = os.getenv("0036683481420f7d06274bd7b343e5cc6e53e5257a")
B2_BUCKET = os.getenv("psikodonus-files")

s3 = boto3.client(
    service_name='s3',
    endpoint_url=B2_ENDPOINT,
    aws_access_key_id=B2_KEY,
    aws_secret_access_key=B2_SECRET,
    config=Config(signature_version='s3v4')
)

def upload_to_b2(file_path, object_name):
    s3.upload_file(file_path, B2_BUCKET, object_name)
    return f"{B2_ENDPOINT}/{B2_BUCKET}/{object_name}"

def download_from_b2(object_name, destination_path):
    s3.download_file(B2_BUCKET, object_name, destination_path)

def delete_from_b2(object_name):
    s3.delete_object(Bucket=B2_BUCKET, Key=object_name)
