FROM public.ecr.aws/lambda/python:3.9

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy function code
COPY app.py ./

# Command for Lambda
CMD ["app.handler"]
