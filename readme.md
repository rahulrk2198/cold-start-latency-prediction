# Cold Start Latency Prediction in Serverless Workflows

This repository contains the dataset and analysis code used for predicting cold start latency in AWS Lambda deployments for predictive maintenance workflows.

## Contents

- `data/log.csv`: Two-week runtime trace of Lambda cold starts
- `notebooks/Cold_Starts_AWS_Analysis.ipynb`: Feature engineering, model training, and evaluation for cold start latency prediction
- `notebooks/Predictive_Maintenance`: Model Training and selection for Predictive Maintenance
- `AWS/requirements.txt`: Dependencies for Docker to install
- `AWS/mlp_model.pkl`: MLP Model chosen for deployment on AWS
- `AWS/Dockerfile`: Dockerfile 
- `AWS/app.py`: Lambda Function Code
- `AWS/predict_lambda.jmx`: JMeter file for generating HTTP requests
- `AWS/simulate_lambda_requests.sh`: Script for scheduling HTTP requests

