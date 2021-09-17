"""Implement Celery task to upload SQuaSH jobs to S3."""

import os

import boto3
import botocore

from .celery import celery

S3_BUCKET = os.environ.get("S3_BUCKET", "squash-dev.data")


def get_s3_uri(key):
    """Make an S3 URI string.

    Parameters
    ----------
    key: `str`
        The specified S3 key.

    Returns
    -------
    s3_uri: `str`
        The S3 URI representing the location of an S3 object in the form:
        s3://<S3_BUCKET>/<key> where S3_BUCKET is the specified S3 bucket and
        key is the specified S3 key.
    """
    s3_uri = "s3://{}/{}".format(S3_BUCKET, key)
    return s3_uri


def download_object(s3_uri):
    """Download an arbitrary S3 object.

    Example of S3 URI: s3://squash.data/88c3f896fe2948788d56bdadfc468812
    """
    _, _, bucket, key = s3_uri.split("/")

    s3 = boto3.resource("s3")

    try:
        obj = s3.Object(bucket, key)
        data = obj.get()["Body"].read()
    except botocore.exceptions.ClientError:
        data = None

    return data


@celery.task(bind=True)
def upload_object(
    self, key, body, metadata=None, acl=None, content_type="application/json"
):
    """Upload an arbitrary object to an S3 bucket.

    Parameters
    ----------
    S3 key : `str`
        The Object's key identifier.
    body : `str` or `bytes`
        Object data
    metadata : `dict`
        Header metadata values. These keys will appear in headers as
        ``x-amz-meta-*``.
    acl : `str`, optional
        A pre-canned access control list. See
        http://boto3.readthedocs.io/en/latest/reference/services/s3.html#bucket
        Default is `None`, meaning that no ACL is applied to the object.
    content_type : `str`, optional
        The object's content type. Default is 'application/json'

    Returns
    -------
    S3 URI of the uploaded object: `str`
        The location of the S3 object uploaded in the form:
        s3://<S3_BUCKET>/<key>

    Note:
    -----

    Boto3 will check these environment variables for credentials:

    AWS_ACCESS_KEY_ID
        The access key for your AWS account.
    AWS_SECRET_ACCESS_KEY
        The secret key for your AWS account.

    """
    s3_uri = ""
    if S3_BUCKET:

        s3 = boto3.resource("s3")

        object = s3.Object(S3_BUCKET, key)

        args = {}

        if metadata is not None:
            args["Metadata"] = metadata
        if acl is not None:
            args["ACL"] = acl
        if content_type is not None:
            args["ContentType"] = content_type

        self.update_state(state="STARTED")
        object.put(Body=body, **args)

        s3_uri = get_s3_uri(key)

    return s3_uri
