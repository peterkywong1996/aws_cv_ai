# aws_cv_ai
Amazon Rekognition for AI-based Object Recognition on Images
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
  6) Link to the database for automatic record updating
- Codes that may involve customization:
- - detect_all(): detect_labels() -> a list of site objects to be detected, out of a pre-trained object pool; currently detected = helmet, gloves, person fallen-down, fire, fire hydrant, crane, truck, scaffolding, guardrail, stop sign, manhole, tripod, rope, gas mask
- - detect_all(): update_item -> the list of updates should be modified according to those labels above
