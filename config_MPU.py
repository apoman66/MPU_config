import boto3
import json
from pprint import pprint


s3 = boto3.client("s3")
config = boto3.client('config')


APPLICABLE_RESOURCES = ["AWS::S3::Bucket"]


def evaluate_compliance(configuration_item, rule_parameters):

    # Start as non-compliant
    compliance_type = 'NON_COMPLIANT'
    annotation = "S3 bucket does NOT have a lifecycle configuration rule " \
                 + "to abort incomplete multi part uploads."

    # Check if resource was deleted
    if configuration_item['configurationItemStatus'] == "ResourceDeleted":
        compliance_type = 'NOT_APPLICABLE'
        annotation = "The resource was deleted."

    # Check resource for applicability
    elif configuration_item["resourceType"] not in APPLICABLE_RESOURCES:
        compliance_type = 'NOT_APPLICABLE'
        annotation = "The rule doesn't apply to resources of type " \
                     + configuration_item["resourceType"] + "."

    # Check bucket for lifecycle configuration
    else:
        print ('Evaluating bucket %s' % (configuration_item['resourceId']))
        #print (configuration_item)
        if 'supplementaryConfiguration' in configuration_item:
            supplementary_configuration = configuration_item['supplementaryConfiguration']
            if 'BucketLifecycleConfiguration' in supplementary_configuration:
                print ('Found Lifecycle configuration...')
                rules = supplementary_configuration['BucketLifecycleConfiguration']['rules']
                for i in range (0, len(rules)):
                    if 'abortIncompleteMultipartUpload' in rules[i]:
                        print ('Found abortIncompleteMultipartUpload rule...')
                        if rules[i]['status'] == 'Enabled':
                            compliance_type = 'COMPLIANT'
                            annotation = 'S3 bucket has a lifecycle configuration rule to abort incomplete multi part uploads.'
                            print ('Rule is enabled...')
                        else:
                            print ('Rule is not enabled...')
        
    return {
        "compliance_type": compliance_type,
        "annotation": annotation
    }


def lambda_handler(event, context):

    invoking_event = json.loads(event['invokingEvent'])
    #print (json.dumps(event))

    # Check for oversized item
    if "configurationItem" in invoking_event:
        configuration_item = invoking_event["configurationItem"]
    elif "configurationItemSummary" in invoking_event:
        configuration_item = invoking_event["configurationItemSummary"]
        
    # pprint (configuration_item)

    # Optional parameters
    rule_parameters = {}
    if 'ruleParameters' in event:
        rule_parameters = json.loads(event['ruleParameters'])

    evaluation = evaluate_compliance(configuration_item, rule_parameters)

    print('Compliance evaluation for %s: %s' % (configuration_item['resourceId'], evaluation["compliance_type"]))
    print('Annotation: %s' % (evaluation["annotation"]))

    response = config.put_evaluations(
       Evaluations=[
           {
               'ComplianceResourceType': invoking_event['configurationItem']['resourceType'],
               'ComplianceResourceId':   invoking_event['configurationItem']['resourceId'],
               'ComplianceType':         evaluation["compliance_type"],
               "Annotation":             evaluation["annotation"],
               'OrderingTimestamp':      invoking_event['configurationItem']['configurationItemCaptureTime']
           },
       ],
       ResultToken=event['resultToken'])