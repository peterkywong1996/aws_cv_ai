# aws_cv_ai
**Amazon Rekognition for AI-based Object Recognition on Images**
- Code logic:
- 1) User uploaded images to S3 database
  2) Automatically triggered lambda_handler()
  3) Triggered process_site_images() to retrieve the uploaded images
  4) Triggered detect_all() to obtain AI results, with post-processing
  5) According to each type of form, customize the form template
     - Hot work: fire, fire hydrant, gloves
     - Lifting: guard rail, stop sign, persons nearby, helmet, crane, truck
     - Confined space: manhole, tripod, rope, gas mask, gloves, guard rail, stop sign, fire, fire hydrant
     - Working at height: scaffolding, guard rail, rope, helmet
  6) Expected output a JSON structure (refer to sample text files)
  7) Link to the database for automatic record updating

**How to run the code (both required an AWS account)**:
- Option A. Configuration on AWS cloud:
     1) Upload the .py code to AWS Lambda as a new function
     2) Define your own S3 & DynamoDB objects
     3) Configure trigger(s) to link up the Lambda function with S3 & DynamoDB
     4) Customize the variable names according to your own data schema
  
- Option B. Configuration on local computer (https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html#installation):
     1) Install python packages on local computer
     2) Input your own AWS authentication creditials
     3) Similar to the cloud-based steps

**Codes that may involve customization**:
- detect_all(): detect_labels() -> a list of site objects to be detected, out of a pre-trained object pool (refer to the full list in AmazonRekognitionLabelsCategoriesMapping_v3.0.xlsx)
- currently detected = helmet, gloves, person fallen-down, fire, fire hydrant, crane, truck, scaffolding, guardrail, stop sign, manhole, tripod, rope, gas mask
- detect_all(): update_item -> the list of updates should be modified according to those labels above
