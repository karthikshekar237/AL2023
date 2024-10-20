from aws_cdk import (
    Stack,
    aws_imagebuilder as imagebuilder
)
from constructs import Construct
import boto3
import os
from configparser import ConfigParser
import json

def content_of_the_file_and_description(dir, componentFileName):
    with open(os.path.join(dir, componentFileName)) as file:
        content = file.read()
        content_as_list = content.split('\n')
        content_dict = {}
        for val in content_as_list:
            if val.split(":")[0] == "phases":
                break
            else:
                try:
                    key = val.split(":")[0].lower()
                    value = val.split(":")[1].strip()
                    content_dict[key] = value
                except IndexError:
                    continue
        if "description" in content_dict.keys():
            description = content_dict["description"]
        else:
            msg = f"""Description is missing in {componentFileName}, Format should be in the following format:-
            name: "<your_company_name>"
            description: "<your component description>"
            schemaVersion: 1.0
            phase:
              <statement>
            """
            print(msg)
            exit(1)
        return content, description

def get_all_components(client):
    all_components = []
    next_token = None
    while True:
        if next_token:
            response = client.list_components(nextToken=next_token)
        else:
            response = client.list_components()
        all_components.extend(response.get('componentVersionList', []))
        next_token = response.get('nextToken')
        if not next_token:
            break
    return all_components

def get_all_recipes(client):
    all_recipes = []
    next_token = None
    while True:
        if next_token:
            response = client.list_image_recipes(nextToken=next_token)
        else:
            response = client.list_image_recipes()
        all_recipes.extend(response.get('imageRecipeSummaryList', []))
        next_token = response.get('nextToken')
        if not next_token:
            break
    return all_recipes

def read_comp_config(config_file):
    config = {}
    current_env = None
    with open(config_file, 'r') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('[') and line.endswith(']'):
                current_env = line[1:-1]
                config[current_env] = []
            else:
                if current_env:
                    config[current_env].append(line)
    return config

def auto_version_components(client, componentName):
    print(f"Auto_version-components: looking for the component {componentName}")
    current_version = 0
    final_version_str = '0.0.0'
    components = get_all_components(client)
    for component in components:
        if component['name'] == componentName:
            print(f"Auto_version_components: found the existing component {component['arn']}")
            current_version = int(component['version'].split(".")[2])
            new_version_int = current_version + 1
            final_version_str = f'0.0.{new_version_int}'
            break
    print(f"Auto_version_components: returning version {final_version_str}")
    return final_version_str

def auto_version_recipes(client, recipeName):
    print(f"Auto_version_recipes: looking for the recipe {recipeName}")
    current_version = 0
    final_version_str = '0.0.0'
    recipes = get_all_recipes(client)
    for recipe in recipes:
        if recipe['name'] == recipeName:
            recipe_response = client.get_image_recipe(imageRecipeArn=recipe['arn'])
            print(f"Auto_version_recipe: found an existing recipe {recipe_response}")
            current_version = int(recipe_response['imageRecipe']['version'].split(".")[2])
            new_version_int = current_version + 1
            final_version_str = f'0.0.{new_version_int}'
            break
    print(f"Auto_version_recipes: returning version {final_version_str}")
    return final_version_str

class Al2023Stack(Stack):
    def __init__(self, scope: Construct, construct_id: str, branch, workspace, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if branch is None:
            branch = "master"

        print(f"You are presently working in \"{branch}\"")

        if workspace == "soe_nonprod" or workspace == "soe_prod":
            configs = ConfigParser()
            configs.read('config.ini')
            conf_dict = {}
            variables = configs.items(workspace)

            for key, value in variables:
                conf_dict[key] = value
                print(key, "=", conf_dict[key])

            amiid = str(conf_dict['amiid'])
            aminame = str(conf_dict['aminame'])
            platform = str(conf_dict['platform'])
            supported_os_versions = json.loads(conf_dict['supported_os_versions'])
            kms_key = str(conf_dict['kms_key'])
            local_path = str(conf_dict['local_path'])
            workingfolder = str(conf_dict['working_folder'])
            recipedesc = str(conf_dict['recipedesc'])
            instance_profile_name = str(conf_dict['instance_profile_name'])
            instance_types = json.loads(conf_dict['instance_types'])
            key_pair = str(conf_dict['key_pair'])
            s3_bucket = str(conf_dict['s3_bucket'])
            s3_bucket_prefix = str(conf_dict['s3_bucket_prefix'])
            security_group_ids = json.loads(conf_dict['security_group_ids'])
            sns_topic_arn = str(conf_dict['sns_topic_arn'])
            subnet_id = str(conf_dict['subnet_id'])
            aws_accounts = json.loads(conf_dict['aws_accounts'])
            region = str(conf_dict['region'])

            recipe_id = str(conf_dict['recipe_id']) + branch
            infraconfig_id = str(conf_dict['infraconfigid']) + branch
            distribution_settings_id = str(conf_dict['distribution_settings_id']) + branch
            imagepipeline_id = str(conf_dict['imagepipelineid']) + branch
            recipe_name = str(conf_dict['recipe_name']) + branch
            infraconfig_name = str(conf_dict['infraconfig_name']) + branch
            distribution_settings_name = str(conf_dict['distribution_settings_name']) + branch
            imagepipeline_name = str(conf_dict['imagepipelinename']) + branch
            stackname = str(conf_dict['stackname']) + branch
            componentname = str(conf_dict['componentname']) + branch
        else:
            print("Workspace value cannot be left null. Terminating current operation")
            exit(1)

        client = boto3.client('imagebuilder')

        components = read_comp_config("components.ini")
        components = components.get(workspace)

        component_arns = []

        for component in components:
            component_name = f"{componentname}-{component.split('.')[0]}".lower().replace("_", "-")
            component_file_name = component
            component_data, component_description = content_of_the_file_and_description(local_path + 'components/', componentFileName=component_file_name)
            version = auto_version_components(client, componentName=component_name)

            id = f"{component_name}"
            cfn_component_response = imagebuilder.CfnComponent(
                self, id, name=component_name, platform=platform, version=version,
                change_description="Creating New version of this component", data=component_data,
                description=component_description, supported_os_versions=supported_os_versions
            )
            component_arns.append(imagebuilder.CfnImageRecipe.ComponentConfigurationProperty(component_arn=cfn_component_response.attr_arn))

        version = auto_version_recipes(client, recipeName=recipe_name)

        cfn_image_recipe_response = imagebuilder.CfnImageRecipe(
            self, recipe_id, components=component_arns, name=recipe_name, parent_image=amiid, version=version,
            additional_instance_configuration=imagebuilder.CfnImageRecipe.AdditionalInstanceConfigurationProperty(
                systems_manager_agent=imagebuilder.CfnImageRecipe.SystemsManagerAgentProperty(uninstall_after_build=False)),
            block_device_mappings=[imagebuilder.CfnImageRecipe.InstanceBlockDeviceMappingProperty(
                device_name="/dev/xvda",
                ebs=imagebuilder.CfnImageRecipe.EbsInstanceBlockDeviceSpecificationProperty(
                    delete_on_termination=True, encrypted=True, iops=150, throughput=125, kms_key_id=kms_key,
                    volume_size=10, volume_type="gp3"))],
            description=recipedesc, working_directory=workingfolder)

        cfn_infrastructure_configuration_response = imagebuilder.CfnInfrastructureConfiguration(
            self, infraconfig_id, name=infraconfig_name,
            description=f"This infrastructureConfiguration is created from CDK code. Stack name:- {stackname}",
            instance_types=instance_types, key_pair=key_pair, instance_profile_name=instance_profile_name,
            logging=imagebuilder.CfnInfrastructureConfiguration.LoggingProperty(
                s3_logs=imagebuilder.CfnInfrastructureConfiguration.S3LogsProperty(
                    s3_bucket_name=s3_bucket, s3_key_prefix=s3_bucket_prefix)),
            security_group_ids=security_group_ids, sns_topic_arn=sns_topic_arn, subnet_id=subnet_id,
            terminate_instance_on_failure=True, resource_tags={"Bootstrap": "false"})

        distributions = [
            imagebuilder.CfnDistributionConfiguration.DistributionProperty(
                region=region,
                ami_distribution_configuration={
                    "AmiTags": {"Name": aminame},
                    "Description": "This AMI Distribution is created through CDK code.",
                    "LaunchPermissionConfiguration": {"UserIds": aws_accounts},
                    "Name": aminame + "-{{ imagebuilder:buildDate }}",
                    "KmsKeyId": kms_key
                }
            )
        ]

        print(f"Creating imagebuilder.CfnDistributionConfiguration: distribution_settings_id: {distribution_settings_id}, distributions: {distributions}, name: {distribution_settings_name}")

        cfn_distribution_configuration_response = imagebuilder.CfnDistributionConfiguration(
            self, distribution_settings_id, distributions=distributions, name=distribution_settings_name)

        cfn_image_pipeline = imagebuilder.CfnImagePipeline(
            self, imagepipeline_id, infrastructure_configuration_arn=cfn_infrastructure_configuration_response.attr_arn,
            name=imagepipeline_name,
            image_scanning_configuration=imagebuilder.CfnImagePipeline.ImageScanningConfigurationProperty(image_scanning_enabled=True),
            description="This pipeline is created using CDK code", enhanced_image_metadata_enabled=True, status="ENABLED",
            distribution_configuration_arn=cfn_distribution_configuration_response.attr_arn,
            image_recipe_arn=cfn_image_recipe_response.attr_arn,
            image_tests_configuration=imagebuilder.CfnImagePipeline.ImageTestsConfigurationProperty(image_tests_enabled=True, timeout_minutes=60),
            tags={"dataclassification": "confidential"})
