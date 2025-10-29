#!/bin/bash
awslocal s3 mb s3://ingestor-raw
awslocal s3 mb s3://ingestor-processed

awslocal dynamodb create-table \
  --table-name files \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
