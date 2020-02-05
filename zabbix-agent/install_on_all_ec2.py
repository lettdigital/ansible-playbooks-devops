import os
import subprocess

import boto3

ec2_client = boto3.client("ec2")
s3_client = boto3.client("s3")


def main():
    reservations = ec2_client.describe_instances()["Reservations"]
    instances_to_run = get_instances_to_run(reservations)
    ssl_keys_directory = get_ssl_keys()

    for instance_to_run in instances_to_run:
        install_zabbix_agent_with_ansible(instance_to_run, ssl_keys_directory)


def install_zabbix_agent_with_ansible(instance_to_run, ssl_keys_directory):
    print(f"installing zabbix-agent on {instance_to_run['name']}...")
    user_to_run = get_user_to_run(instance_to_run)
    subprocess.run(
        f"""
            ansible {instance_to_run['private_ip']} -i {instance_to_run['private_ip']}, \
                --user={user_to_run} \
                --key-file={os.path.join(ssl_keys_directory, instance_to_run['key_pair'])}.pem \
                --module-name=import_role \
                --args name=zabbix-agent
            """,
        shell=True,
        check=True,
        cwd=os.path.join(os.getcwd(), "..")
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


def get_instances_to_run(reservations):
    print("getting instances to run...")
    instances = (instance
                 for reservation in reservations
                 for instance in reservation["Instances"])
    instances_to_run = [{"key_pair": instance["KeyName"],
                         "name": get_instance_tag(instance, "Name"),
                         "private_ip": instance["PrivateIpAddress"]}
                        for instance in instances
                        if get_instance_tag(instance, "elasticbeanstalk:environment-name") is None]
    return instances_to_run


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
