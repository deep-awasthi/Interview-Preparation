# SDK & AWS CLI Integration Guide

Aether is designed so that applications can switch between AWS S3 and Aether by changing only the `endpoint_url`.

## Python (boto3)

```python
import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:8000",
    aws_access_key_id="admin",
    aws_secret_access_key="password",
    region_name="us-east-1",
)

# Create bucket
s3.create_bucket(Bucket="my-app-data")

# Put Object
s3.put_object(Bucket="my-app-data", Key="images/photo.png", Body=open("photo.png", "rb"))

# Get Object
response = s3.get_object(Bucket="my-app-data", Key="images/photo.png")
data = response["Body"].read()
```

## AWS CLI

```bash
aws --endpoint-url http://localhost:8000 s3 mb s3://my-cli-bucket
aws --endpoint-url http://localhost:8000 s3 cp myfile.txt s3://my-cli-bucket/
aws --endpoint-url http://localhost:8000 s3 ls s3://my-cli-bucket/
```

## Go SDK (aws-sdk-go-v2)

```go
cfg, err := config.LoadDefaultConfig(context.TODO(),
    config.WithEndpointResolverWithOptions(aws.EndpointResolverWithOptionsFunc(
        func(service, region string, options ...interface{}) (aws.Endpoint, error) {
            return aws.Endpoint{
                URL: "http://localhost:8000",
                SigningRegion: "us-east-1",
            }, nil
        })),
)
client := s3.NewFromConfig(cfg)
```
