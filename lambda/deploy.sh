#!/bin/bash
set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Configuration
FUNCTION_NAME="email-sender"
BUCKET_NAME="riseportraits-lambda-deployment"
EMAIL_LISTS_BUCKET="riseportraits-email-lists"
EMAIL_TEMPLATES_BUCKET="riseportraits-email-templates"
REGION="eu-west-2"
RUNTIME="python3.12"
HANDLER="lambda_function.lambda_handler"
MEMORY_SIZE=256
TIMEOUT=300
ROLE_ARN="arn:aws:iam::253490754480:role/lambda-email-sender-role"

# Create deployment package
echo "Creating deployment package..."
zip -r function.zip src/lambda_function.py

# Upload function code to S3
echo "Uploading function code to S3..."
aws s3 cp function.zip s3://${BUCKET_NAME}/functions/${FUNCTION_NAME}.zip

# Create or update Lambda function
echo "Creating/updating Lambda function..."
aws lambda create-function \
    --function-name ${FUNCTION_NAME} \
    --runtime python3.12 \
    --role ${ROLE_ARN} \
    --handler ${HANDLER} \
    --code S3Bucket=${BUCKET_NAME},S3Key=functions/${FUNCTION_NAME}.zip \
    --timeout ${TIMEOUT} \
    --memory-size ${MEMORY_SIZE} \
    --environment Variables={SENDER_EMAIL=contact@riseportraits.co.uk} \
    --region ${REGION} || \
aws lambda update-function-code \
    --function-name ${FUNCTION_NAME} \
    --s3-bucket ${BUCKET_NAME} \
    --s3-key functions/${FUNCTION_NAME}.zip \
    --region ${REGION}

# Create EventBridge rules for scheduled triggers
echo "Creating EventBridge rules..."

# 8am UK time
aws events put-rule \
    --name "${FUNCTION_NAME}-8am" \
    --schedule-expression "cron(0 8 * * ? *)" \
    --state ENABLED \
    --region "${REGION}"

aws events put-targets \
    --rule "${FUNCTION_NAME}-8am" \
    --targets "Id=1,Arn=arn:aws:lambda:${REGION}:253490754480:function:${FUNCTION_NAME}" \
    --region "${REGION}"

# 11am UK time
aws events put-rule \
    --name "${FUNCTION_NAME}-11am" \
    --schedule-expression "cron(0 11 * * ? *)" \
    --state ENABLED \
    --region "${REGION}"

aws events put-targets \
    --rule "${FUNCTION_NAME}-11am" \
    --targets "Id=1,Arn=arn:aws:lambda:${REGION}:253490754480:function:${FUNCTION_NAME}" \
    --region "${REGION}"

# 4pm UK time
aws events put-rule \
    --name "${FUNCTION_NAME}-4pm" \
    --schedule-expression "cron(0 16 * * ? *)" \
    --state ENABLED \
    --region "${REGION}"

aws events put-targets \
    --rule "${FUNCTION_NAME}-4pm" \
    --targets "Id=1,Arn=arn:aws:lambda:${REGION}:253490754480:function:${FUNCTION_NAME}" \
    --region "${REGION}"

echo "Deployment completed!" 