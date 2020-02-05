import argparse
import os
import pickle
import re
import subprocess

import boto3
from pyzabbix import ZabbixAPI

ec2_client = boto3.client("ec2")
s3_client = boto3.client("s3")
zapi = ZabbixAPI(url=os.environ.get("ZABBIX_SERVER", "https://localhost"),
                 user=os.environ.get("ZABBIX_AUTOMATION_USER"),
                 password=os.environ.get("ZABBIX_AUTOMATION_PASSWORD"))


def main():
    pickle_filename = "success_ec2_ids.pkl"
    args = get_args()
    zabbix_major_version = get_zabbix_major_version()
    success_ec2_ids = get_previous_successful_ec2_ids(pickle_filename)
    errored_instances = install_zabbix_agent_on_instances(args, success_ec2_ids, zabbix_major_version)
    save_successful_instance_ids(pickle_filename, success_ec2_ids)
    print_conclusion_message(errored_instances)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--update-all",
                        default=False,
                        action="store_true")
    args = parser.parse_args()
    return args


def print_conclusion_message(errored_instances):
    if errored_instances:
        print("the following instances installations errored !!!")
        for instance in errored_instances:
            print(f"{instance['name']}: {instance['id']}")
    else:
        print("all installations were successful!")


def get_zabbix_major_version():
    zabbix_major_version = (re.match("(\d+.\d+).\d+",
                                     zapi.api_version())
                            .group(1))
    return zabbix_major_version


def install_zabbix_agent_on_instances(args, success_ec2_ids, zabbix_major_version):
    reservations = ec2_client.describe_instances()["Reservations"]
    ssl_keys_directory = get_ssl_keys()
    instances_to_run = get_instances_to_run(reservations, success_ec2_ids, args.update_all)
    errored_instances = []
    for instance_to_run in instances_to_run:
        try:
            install_zabbix_agent_with_ansible(instance_to_run, ssl_keys_directory, zabbix_major_version)
            success_ec2_ids.add(instance_to_run['id'])
        except subprocess.CalledProcessError:
            errored_instances.append(instance_to_run)
    return errored_instances


def save_successful_instance_ids(pickle_filename, success_ec2_ids):
    with open(pickle_filename, "wb") as success_ec2_ids_pkl:
        pickle.dump(success_ec2_ids, success_ec2_ids_pkl)


def get_previous_successful_ec2_ids(pickle_filename):
    if os.path.isfile(pickle_filename):
        with open(pickle_filename, "rb") as success_ec2_ids_pkl:
            success_ec2_ids = pickle.load(success_ec2_ids_pkl)
    else:
        success_ec2_ids = set()
    return success_ec2_ids


def install_zabbix_agent_with_ansible(instance_to_run, ssl_keys_directory, zabbix_major_version):
    print(f"installing zabbix-agent on {instance_to_run['name']}...")
    user_to_run = get_user_to_run(instance_to_run)
    subprocess.run(
        f"""
            ansible {instance_to_run['private_ip']} -i {instance_to_run['private_ip']}, \
                --user={user_to_run} \
                --key-file={os.path.join(ssl_keys_directory, instance_to_run['key_pair'])}.pem \
                --extra-vars="zabbix_major_version={zabbix_major_version}" \
                --module-name=import_role \
                --args name=zabbix-agent
            """,
        shell=True,
        check=True,
        cwd=os.path.join(os.path.realpath(__file__), "..")
    )


def get_ssl_keys():
    ssl_keys_directory = "/tmp/ssl-keys"
    os.makedirs(ssl_keys_directory, exist_ok=True)
    print("getting ssl keys...")
    subprocess.run(f"aws s3 sync s3://lett-ssh-keys {ssl_keys_directory}",
                   shell=True,
                   check=True)
    subprocess.run(f"chmod 600 {os.path.join(ssl_keys_directory, '*')}",
                   shell=True,
                   check=True)
    return ssl_keys_directory


def get_instances_to_run(reservations, success_ec2_ids, update_all):
    print("getting instances to run...")
    instances = (instance
                 for reservation in reservations
                 for instance in reservation["Instances"])
    instances_to_run = [{"key_pair": instance["KeyName"],
                         "id": instance["InstanceId"],
                         "name": get_instance_tag(instance, "Name"),
                         "private_ip": instance["PrivateIpAddress"]}
                        for instance in instances
                        if should_run_on_instance(instance, success_ec2_ids, update_all)]
    return instances_to_run


def should_run_on_instance(instance, success_ec2_ids, update_all):
    ec2_is_beanstalk = get_instance_tag(instance, "elasticbeanstalk:environment-name") is not None

    return (not ec2_is_beanstalk
            and (update_all or instance["InstanceId"] not in success_ec2_ids))


def get_user_to_run(instance_to_run):
    try:
        subprocess.run(
            f"ssh -q -i /tmp/ssl-keys/{instance_to_run['key_pair']}.pem ubuntu@{instance_to_run['private_ip']} exit",
            check=True,
            shell=True
        )
        user_to_run = "ubuntu"
    except subprocess.CalledProcessError:
        user_to_run = "ec2-user"

    return user_to_run


def get_instance_tag(instance, tag_name):
    try:
        return next(tag["Value"] for tag in instance["Tags"] if tag["Key"] == tag_name)
    except StopIteration:
        return None


if __name__ == "__main__":
    main()
