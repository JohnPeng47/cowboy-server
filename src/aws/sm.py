import boto3
from botocore.exceptions import ClientError

from src.config import AWS_REGION


class SecretManager:
    def __init__(self, region_name=AWS_REGION):
        """Initialize the ParameterManager with a specific AWS region."""
        self.client = boto3.client("ssm", region_name=region_name)

    def store_parameter(self, name, value, description="", key_id=None):
        """
        Store a parameter in AWS Parameter Store.

        :param name: Name of the parameter.
        :param value: Value of the parameter.
        :param description: Description of the parameter.
        :param key_id: The ID of the KMS key to use for encryption. If None, the default KMS key is used.
        :return: Response from the put_parameter call.
        """
        try:
            params = {
                "Name": name,
                "Value": value,
                "Type": "SecureString" if key_id else "String",
                "Description": description,
                "Overwrite": True,
            }
            if key_id:
                params["KeyId"] = key_id

            response = self.client.put_parameter(**params)
            return response
        except ClientError as e:
            print(f"An error occurred: {e}")
            return None

    def retrieve_parameter(self, name, with_decryption=True):
        """
        Retrieve a parameter from AWS Parameter Store.

        :param name: Name of the parameter.
        :param with_decryption: Whether to decrypt the parameter value.
        :return: The parameter value.
        """
        try:
            response = self.client.get_parameter(
                Name=name, WithDecryption=with_decryption
            )
            return response["Parameter"]["Value"]
        except ClientError as e:
            print(f"An error occurred: {e}")
            return None


# Example usage:
if __name__ == "__main__":
    region = "us-east-2"
    param_manager = SecretManager(region_name=region)

    # Store a parameter
    param_name = "MySecret"
    param_value = "SuperSecretValue"
    response = param_manager.store_parameter(
        name=param_name, value=param_value, description="A test secret parameter"
    )
    if response:
        print(f"Parameter {param_name} stored successfully.")

    # Retrieve a parameter
    retrieved_value = param_manager.retrieve_parameter(name=param_name)
    if retrieved_value:
        print(f"Retrieved value: {retrieved_value}")
