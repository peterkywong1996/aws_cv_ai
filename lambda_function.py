import boto3
import urllib.request
import urllib.parse
import urllib.error


#------define AWS API objects------
s3_client = boto3.client('s3', region_name='ap-southeast-1')
rekognition_client = boto3.client('rekognition')


#------Helper Functions to call AWS Rekognition APIs------

def detect_labels(bucket, key):
    response = rekognition_client.detect_labels(Image={"S3Object": {"Bucket": bucket, "Name": key}},
        MaxLabels=5, MinConfidence=30,
        Settings={"GeneralLabels": {"LabelInclusionFilters": [
                "Worker",
                "Fallen Person",
                "Metalworking",
                "Welding",
                "Woodworking",
                "Workshop",
                "Hole",
                "Manhole",
                "Gas Mask",
                "Tripod",
                "Guard Rail",
                "Rope",
                "Vest",
                "Fire Hydrant",
                "Truck",
                "Construction Crane"
                ]
            }
        }
    )
    
    print('Detected {} labels for {}:\n'.format(len(response['Labels']), key))
    for label in response['Labels']:
        print("Label: " + label['Name'])
        print("Confidence: " + str(label['Confidence']))
        print("Instances:")
    
        for instance in label['Instances']:
            print("\nBounding box")
            print(" Top: " + str(instance['BoundingBox']['Top']))
            print(" Left: " + str(instance['BoundingBox']['Left']))
            print(" Width: " + str(instance['BoundingBox']['Width']))
            print(" Height: " + str(instance['BoundingBox']['Height']))
            print(" Confidence: " + str(instance['Confidence']))
    
        print("\nParents:")
        for parent in label['Parents']:
            print(" " + parent['Name'])
        
        print("\nAliases:")
        for alias in label['Aliases']:
            print(" " + alias['Name'])
            print("Categories:")
        
        print("\nCategories:")
        for category in label['Categories']:
            print(" " + category['Name'])

    if "ImageProperties" in str(response):
        print("Background:")
        print(response["ImageProperties"]["Background"])
        print()
        print("Foreground:")
        print(response["ImageProperties"]["Foreground"])
        print()
        print("Quality:")
        print(response["ImageProperties"]["Quality"])
        print()
    
    # Sample code to write response to DynamoDB table 'test_Rekognition' with 'PartK' as Primary Key.
    # Note: role used for executing this Lambda function should have write access to the table.
    table = boto3.resource('dynamodb').Table('test_Rekognition_labels')
    answers = {}
    answers_ = []
    for label in response['Labels']:
        answers_.append(label['Name'])
    answers['Labels'] = answers_
    labels = [answers]
    table.put_item(Item={'PartK': key, 'Labels': labels})
    
    return response

def detect_all(bucket, key, formType, id):

    #---detect specific PPE first---
    response_1 = rekognition_client.detect_protective_equipment(Image={"S3Object": {"Bucket": bucket, "Name": key}},
        SummarizationAttributes = {
            'MinConfidence': 50,
            'RequiredEquipmentTypes': [
                'HEAD_COVER',
                'FACE_COVER'
                'HAND_COVER'
            ]
        }
    )
    
    #---detect other site objects---
    #---user-defined list of objects to detect---
    response_2 = rekognition_client.detect_labels(Image={"S3Object": {"Bucket": bucket, "Name": key}},
        MaxLabels=12, MinConfidence=40,
        Settings={"GeneralLabels": {"LabelInclusionFilters": [
                "Fallen Person",
                "Fire",
                "Fire Hydrant",
                "Construction Crane",
                "Truck",
                "Scaffolding",
                "Guard Rail",
                "Stopsign",
                "Manhole",
                "Tripod",
                "Rope",
                "Gas Mask"
                ]
            }
        }
    )
    
    answers = {
        "NoHelmet": 0,
        "NoGloves": 0,
        "NoMask": 0,
        "Fallen Person": False,
        "Fire": False,
        "Fire Hydrant": False,
        "Construction Crane": False,
        "Truck": False,
        "Scaffolding": False,
        "Guard Rail": False,
        "Stopsign": False,
        "Manhole": False,
        "Tripod": False,
        "Rope": False,
        "Gas Mask": False
    }
    
    PPE_counts = {
        'FACE': 0,
        'HAND': 0,
        'HEAD': 0,
    }
    
    for person in response_1['Persons']:
        hand_counted = None
        for bodyPart in person['BodyParts']:
            if bodyPart['Name'] == 'LEFT_HAND' or bodyPart['Name'] == 'RIGHT_HAND':
                if hand_counted is None:
                    PPE_counts['HAND'] += len(bodyPart['EquipmentDetections'])
                else:
                    hand_counted = True
            else:
                PPE_counts[bodyPart['Name']] += len(bodyPart['EquipmentDetections'])
    
    numPersons = len(response_1['Persons'])
    answers['NoHelmet'] = numPersons - PPE_counts['HEAD']
    answers['NoMask'] = numPersons - PPE_counts['FACE']
    answers['NoGloves'] = numPersons - PPE_counts['HAND']
    answers['WithHelmet'] = PPE_counts['HEAD']
    answers['WithMask'] = PPE_counts['FACE']
    answers['WithGloves'] = PPE_counts['HAND']
    
    for label in response_2['Labels']:
        answers[label['Name']] = True
    

    #---prepare for database updating, according to which type of form was submitted by users---
    table = boto3.resource('dynamodb').Table('forms')
    

    if formType == '熱工序許可證':
        fireCheck = '存在' if answers['Fire'] else '不存在'
        fireExtinguisherCheck = '存在' if answers['Fire Hydrant'] else '不存在'
        fireSafety = ''
        if answers['WithGloves'] > 0:
            fireSafety += '{}人有戴手套 '.format(answers['WithGloves'])
        if answers['NoGloves'] > 0:
            fireSafety += '{}人無戴手套 '.format(answers['NoGloves'])
        
        try:
            response = table.update_item(
                Key={'formType': formType, 'id': id},
                UpdateExpression='set \
                    formData.fireCheck=:fc, \
                    formData.fireExtinguisherCheck=:fe, \
                    formData.fireSafety=:fs', 
                ExpressionAttributeValues={
                    ':fc': fireCheck,
                    ':fe': fireExtinguisherCheck,
                    ':fs': fireSafety
                },
                ReturnValues="UPDATED_NEW",
            )
            print('Response:\n', response)
        except Exception as e:
            raise e
    
    
    elif formType == '吊運許可證-接近公眾地方(紅區)':
        if not answers['Guard Rail'] or not answers['Stopsign'] or numPersons > 0:
            warningCheck = '不是'
        warningNotes = ''
        if answers['Guard Rail']:
            warningNotes += '有圍欄 '
        else:
            warningNotes += '無圍欄 '
        if answers['Stopsign']:
            warningNotes += '有警告牌 '
        else:
            warningNotes += '無警告牌 '
        if numPersons > 0:
            warningNotes += '有人在附近 '
        else:
            warningNotes += '無人在附近 '
        
        inspectionNotes = '有{}人在現場 '.format(numPersons) if numPersons > 0 else '無人在現場 '
        
        trainingCheck = '是'
        trainingNotes = ''
        if answers['WithHelmet'] > 0:
            trainingNotes += '{}人有戴安全帽 '.format(answers['WithHelmet'])
        if answers['NoHelmet'] > 0:
            trainingNotes += '{}人無戴安全帽 '.format(answers['NoHelmet'])
            trainingCheck = '不是'
        
        liftMachineType = ''
        if answers['Construction Crane']:
            liftMachineType += '大吊 '
        if answers['Truck']:
            liftMachineType += '吊雞車 '
    
        try:
            response = table.update_item(
                Key={'formType': formType, 'id': id},
                UpdateExpression='set \
                    formData.warningCheck=:wc, \
                    formData.warningNotes=:wn, \
                    formData.inspectionCheck=:ic, \
                    formData.inspectionNotes=:in, \
                    formData.trainingCheck=:tc, \
                    formData.trainingNotes=:tn, \
                    formData.liftMachineType=:lm',
                ExpressionAttributeValues={
                    ':wc': warningCheck,
                    ':wn': warningNotes,
                    ':ic': inspectionCheck,
                    ':in': inspectionNotes,
                    ':tc': trainingCheck,
                    ':tn': trainingNotes,
                    ':lm': liftMachineType
                },
                ReturnValues="UPDATED_NEW",
            )
            print('Response:\n', response)
        except Exception as e:
            raise e
    

    elif formType == '密閉空間許可證':
        fireRiskCheck = '存在' if answers['Fire'] else '不存在'
        fireRiskSafety = '滅火筒' if answers['Fire Hydrant'] else ''
        
        if answers['WithMask'] > 0 or answers['Gas Mask']:
            gasRiskCheck = '存在'
            gasRiskSafety = '有戴防毒面罩/口罩 '
        else:
            gasRiskCheck = '不存在'
            gasRiskSafety = ''
        
        hotWorkRiskCheck = '存在' if answers['WithGloves'] > 0 else '不存在'
        hotWorkRiskSafety = '{}人有戴手套 '.format(answers['WithGloves'])
        if answers['NoGloves'] > 0:
            hotWorkRiskSafety += '{}人無戴手套 '.format(answers['NoGloves'])
        
        chemicalRiskCheck = '存在'
        chemicalRiskSafety = '{}人有戴手套 '.format(answers['WithGloves'])
        if answers['NoGloves'] > 0:
            chemicalRiskSafety += '{}人無戴手套 '.format(answers['NoGloves'])
            
        environmentalRiskCheck = '存在' if answers['Manhole'] or answers['Guard Rail'] or answers['Stopsign'] else '不存在'
        environmentalRiskSafety = ''
        if answers['Manhole']:
            environmentalRiskSafety += '有沙井/樓洞/缺口 '
        if answers['Guard Rail']:
            environmentalRiskSafety += '有圍欄 '
        else:
            environmentalRiskSafety += '無圍欄 '
        if answers['Stopsign']:
            environmentalRiskSafety += '有警告牌 '
        else:
            environmentalRiskSafety += '無警告牌 '
        if answers['Tripod']:
            environmentalRiskSafety += '有三腳架 '
        else:
            environmentalRiskSafety += '無三腳架 '
        
        workAtHeightRiskCheck = '存在' if answers['Scaffolding'] or answers['Guard Rail'] else '不存在'
        workAtHeightRiskSafety = ''
        if answers['Scaffolding']:
            workAtHeightRiskSafety += '有棚架 '
        if answers['Guard Rail']:
            workAtHeightRiskSafety += '有圍欄 '
        else:
            workAtHeightRiskSafety += '無圍欄 '
        if answers['Rope']:
            workAtHeightRiskSafety += '有安全繩 '
        else:
            workAtHeightRiskSafety += '無安全繩 '
        if answers['WithHelmet'] > 0:
            workAtHeightRiskSafety += '{}人有戴安全帽 '.format(answers['WithHelmet'])
        if answers['NoHelmet'] > 0:
            workAtHeightRiskSafety += '{}人無戴安全帽 '.format(answers['NoHelmet'])
        
        try:
            response = table.update_item(
                Key={'formType': formType, 'id': id},
                UpdateExpression='set \
                    formData.fireRiskCheck=:fc, \
                    formData.fireRiskSafety=:fs, \
                    formData.gasRiskCheck=:gc, \
                    formData.gasRiskSafety=:gs, \
                    formData.hotWorkRiskCheck=:hc, \
                    formData.hotWorkRiskSafety=:hs, \
                    formData.chemicalRiskCheck=:cc, \
                    formData.chemicalRiskSafety=:cs, \
                    formData.environmentalRiskCheck=:ec, \
                    formData.environmentalRiskSafety=:es, \
                    formData.workAtHeightRiskCheck=:wc, \
                    formData.workAtHeightRiskSafety=:ws',
                ExpressionAttributeValues={
                    ':fc': fireRiskCheck,
                    ':fs': fireRiskSafety,
                    ':gc': gasRiskCheck,
                    ':gs': gasRiskSafety,
                    ':hc': hotWorkRiskCheck,
                    ':hs': hotWorkRiskSafety,
                    ':cc': chemicalRiskCheck,
                    ':cs': chemicalRiskSafety,
                    ':ec': environmentalRiskCheck,
                    ':es': environmentalRiskSafety,
                    ':wc': workAtHeightRiskCheck,
                    ':ws': workAtHeightRiskSafety
                },
                ReturnValues="UPDATED_NEW",
            )
            print('Response:\n', response)
        except Exception as e:
            raise e
    
    else:
        print('No form type matched')
    
    return [response_1, response_2]


def process_site_images(event):
    eventName = event['Records'][0]['eventName']
    
    formType = event['Records'][0]['dynamodb']['NewImage']['formType']['S']
    id = event['Records'][0]['dynamodb']['NewImage']['id']['S']
    
    formData_new = event['Records'][0]['dynamodb']['NewImage']['formData']['M']
    image_urls_new = formData_new['siteImages']['L'] if 'siteImages' in formData_new.keys() else formData_new['siteImage']['L']
    image_urls_new = [image_url['S'] for image_url in image_urls_new]
    
    if eventName == 'MODIFY': #INSERT
        formData_old = event['Records'][0]['dynamodb']['OldImage']['formData']['M']
        image_urls_old = formData_old['siteImages']['L'] if 'siteImages' in formData_old.keys() else formData_old['siteImage']['L']
        image_urls_old = [image_url['S'] for image_url in image_urls_old]
    
    response_1, response_2 = None, None
    
    for image_url_new in image_urls_new:
        if eventName == 'MODIFY':
            if image_url_new in image_urls_old:
                continue
        
        #---get the S3 folder and image file names
        image_directory = image_url_new.split('bucketName=')[1]
        bucket, key = image_directory.split('&fileName=')
        
        try:
            #---call rekognition DetectLabels & DetectProtectiveEquipment APIS in S3 object---
            response_1, response_2 = detect_all(bucket, key, formType, id)
        
        except Exception as e:
            raise e
            
    return [response_1, response_2]
    

# --------------- Main handler ------------------

def lambda_handler(event, context):
    try:
        response = process_site_images(event)
        return response
        
    except Exception as e:
        raise e