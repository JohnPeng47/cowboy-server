import boto3
from botocore.exceptions import ClientError

from src.config import AWS_REGION


class SQS:
    def __init__(self, queue_name, region_name=AWS_REGION):
        self.sqs = boto3.client("sqs", region_name=region_name)
        self.queue_name = queue_name
        self.queue_url = self.create_fifo_queue(queue_name)

    def create_fifo_queue(self, queue_name):
        try:
            response = self.sqs.create_queue(
                QueueName=f"{queue_name}.fifo",
                Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
            )
            return response["QueueUrl"]
        except ClientError as e:
            print(f"An error occurred: {e}")
            return None

    def put(self, message_body, message_deduplication_id=None):
        try:
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message_body,
                MessageDeduplicationId=message_deduplication_id or message_body,
            )
            return response
        except ClientError as e:
            print(f"An error occurred: {e}")
            return None

    def receive(self, max_number_of_messages=1, wait_time_seconds=0):
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_number_of_messages,
                WaitTimeSeconds=wait_time_seconds,
            )
            return response.get("Messages", [])
        except ClientError as e:
            print(f"An error occurred: {e}")
            return None

    def peek(self, max_number_of_messages=1):
        return self.receive(
            max_number_of_messages=max_number_of_messages, wait_time_seconds=0
        )
