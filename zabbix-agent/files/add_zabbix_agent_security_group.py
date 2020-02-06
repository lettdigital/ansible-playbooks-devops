import sys
import os

import boto3

zabbix_agent_security_group_names = {
    "production": os.environ["ZABBIX_AGENT_SG_NAME_PROD"],
    "development": os.environ["ZABBIX_AGENT_SG_NAME_DEV"]
}
production_vpc_name = os.environ["PRODUCTION_VPC_NAME"]

ec2_client = boto3.client("ec2")
ec2_resource = boto3.resource("ec2")


def main():
    instance, instance_info = get_instance_class_and_info()
    vpc_names_by_id = get_vpc_names_by_id()
    instance_security_group_ids = get_instance_security_group_ids(instance_info)
    security_group_pages = ec2_client.get_paginator('describe_security_groups').paginate()
    security_group_ids_by_name = get_zabbix_security_group_ids_by_names(security_group_pages)
    security_group_ids_to_add = get_security_ids_to_add_to_instance(instance_info,
                                                                    instance_security_group_ids,
                                                                    security_group_ids_by_name, vpc_names_by_id)
    instance.modify_attribute(Groups=list(security_group_ids_to_add))
    print("Success")


def get_security_ids_to_add_to_instance(instance_info,
                                        instance_security_group_ids,
                                        security_group_ids_by_name,
                                        vpc_names_by_id):
    zabbix_security_group_to_add = (security_group_ids_by_name[zabbix_agent_security_group_names["production"]]
                                    if vpc_names_by_id[instance_info["VpcId"]] == production_vpc_name
                                    else security_group_ids_by_name[zabbix_agent_security_group_names["development"]])
    security_group_ids_to_add = {*instance_security_group_ids,
                                 zabbix_security_group_to_add}
    return security_group_ids_to_add


def get_zabbix_security_group_ids_by_names(security_group_pages):
    security_groups = (security_group
                       for page in security_group_pages
                       for security_group in page["SecurityGroups"])
    zabbix_security_groups = (security_group
                              for security_group in security_groups
                              if "zabbix-agent" in security_group["GroupName"])
    security_group_ids_by_name = {security_group["GroupName"]: security_group["GroupId"]
                                  for security_group in zabbix_security_groups}
    return security_group_ids_by_name


def get_instance_security_group_ids(instance_info):
    instance_security_group_ids = {security_group["GroupId"]
                                   for security_group in instance_info["SecurityGroups"]}
    return instance_security_group_ids


def get_vpc_names_by_id():
    vpc_names_by_id = {vpc["VpcId"]: next(tag["Value"]
                                          for tag in vpc["Tags"]
                                          if tag["Key"] == "Name")
                       for vpc in ec2_client.describe_vpcs()["Vpcs"]}
    return vpc_names_by_id


def get_instance_class_and_info():
    instance_id = sys.argv[1]
    instance_info = ec2_client.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
    instance = ec2_resource.Instance(instance_info["InstanceId"])
    return instance, instance_info


main()
