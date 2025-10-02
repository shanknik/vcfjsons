"""
Filename:
    wld-default-cluster-replacement.py

Description:
    This script assists in the replacement of the default cluster in a workload domain by updating the SDDC Manager database.

Author:
    Sowjanya V
"""
import datetime
import getpass
import json
import logging
import re
import os
import sys
import subprocess
import time
import requests
import pexpect
from colorama import init
from colorama import Fore, Back, Style

BASE_URL = 'http://localhost/inventory'

init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log messages."""

    COLORS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
    }

    def format(self, record):
        # Add color based on the log level
        color = self.COLORS.get(record.levelno, "")
        record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)

class NoColorFormatter(logging.Formatter):
    """
    Log formatter that strips terminal colour
    escape codes from the log message.
    """

    # Regex for ANSI colour codes
    ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

    def format(self, record):
        """Return logger message with terminal escapes removed."""
        return "%s %s %s" % (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            re.sub(self.ANSI_RE, "", record.levelname),
            re.sub(self.ANSI_RE, "", record.msg),
        )

class BackupPaths:
    """This class consists of static methods to create the database backup file"""
    @staticmethod
    def edge_cluster(timestamp):
        """returns the name of the file to store database backup"""
        return f'/tmp/db-dump-ec-vc_{timestamp}.gz'

    @staticmethod
    def vcenter_datastore(timestamp):
        """returns the name of the file to store database backup"""
        return f'/tmp/db-dump-vc-ds_{timestamp}.gz'

    @staticmethod
    def default_cluster(timestamp):
        """returns the name of the file to store database backup"""
        return f'/tmp/db-dump-dvc_{timestamp}.gz'

# Get the script name and current timestamp
script_name = os.path.splitext(os.path.basename(__file__))[0]
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = f"{script_name}_{timestamp}.log"
#logging.getLogger().propagate = False

# Configure logging to write to both console and file
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.INFO)
formatter = NoColorFormatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Create a console handler
console_handler = logging.StreamHandler()
# Add the custom formatter to the handler
console_formatter = ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)

#file_handler.propagate = False
logging.getLogger().addHandler(console_handler)
logging.getLogger().addHandler(file_handler)

if len(logging.getLogger().handlers) > 0:
    # Remove the first handler
    logging.getLogger().removeHandler(logging.getLogger().handlers[0])


def get_from_database(command):
    """Execute a SQL command and return the result as a list of dictionaries."""
    try:
        write_to_file(command)
        command = "psql --host localhost -U postgres platform -q < command.sql"
        ps = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        stdout = ps.stdout.readlines()
        output = []

        keys = []
        for index, line in enumerate(stdout):
            if index == 0:
                keys = [key.strip() for key in line.decode("utf8").split("|")]
            elif index not in (1, len(stdout) - 2, len(stdout) - 1):
                values = [value.strip() for value in line.decode("utf8").split("|")]
                output.append(dict(zip(keys, values)))
        return output
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with error: {e}")
        return []

def read_from_json(filename):
    """Read JSON data from a file and return it as a dictionary."""
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logging.error("The file was not found.")
    except json.JSONDecodeError:
        logging.error("Error decoding JSON.")

def restart_service(name):
    """Restart a system service."""
    try:
        command = f"systemctl restart {name}"
        if getpass.getuser() != "root":
            execute_command(command)
        else:
            subprocess.run(command, shell=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with error: {e}")

def execute_curl(endpoint):
    """Send a GET request to the specified endpoint and return the JSON response."""
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def write_to_file(command):
    """Write a SQL command to a file."""
    with open("command.sql", "w") as sql_file:
        sql_file.write(command)

def take_database_dump(file_path):
    """Take a database dump and save it to the specified file path."""
    command = f'/usr/pgsql/15/bin/pg_dumpall -U postgres -w -h localhost | gzip -f > {file_path}'
    execute_command(command)
    time.sleep(2)
    retries = 3
    while retries > 0:
        if os.path.isfile(file_path):
            logging.info(f"{file_path} exists.")
            command = f"chmod 755 {file_path}"
            execute_command(command)
            logging.info(f"Permissions for {file_path} set to 755.")
            break
        else:
            logging.error(f"{file_path} does not exist. Retrying...")
            execute_command(command)
            time.sleep(2)
            retries -= 1

    if retries == 0:
        logging.error(f"Failed to create {file_path} after multiple attempts.")
        sys.exit()

def update_database(sql_command):
    """Update the database with the specified SQL command."""
    write_to_file(sql_command)
    command = "psql --host localhost -U postgres platform < command.sql"
    result = subprocess.run(command, capture_output=True, shell=True, text=True)

    if ("UPDATE 0" in result.stdout):
        logging.info(f"Database is already udpated, no modifications required")

def execute_command(command):
    """Switch to the root user and run the specified command."""
    child = pexpect.spawn('su - root')
    child.sendline(command)
    child.expect('#')
    logging.info(child.before.decode('utf-8'))

def update_default_cluster(db_backup_path, src_cluster, target_cluster):
    """Update the default cluster in the database."""
    take_database_dump(db_backup_path)
    response = execute_curl('clusters')

    src_cluster_id = next((item['id'] for item in response if item['name'] == src_cluster), "")
    target_cluster_id = next((item['id'] for item in response if item['name'] == target_cluster), "")

    logging.info(f"Source Cluster ID: {src_cluster_id}")
    logging.info(f"Destination Cluster ID: {target_cluster_id}")

    update_database(f"update cluster set is_default='t' where id='{target_cluster_id}';")
    update_database(f"update cluster set is_default='f' where id='{src_cluster_id}';")

    response = execute_curl('clusters')
    for item in response:
        if item['name'] == src_cluster:
            logging.info(f"The update {'successful' if not item['isDefault'] else 'unsuccessful'} for source cluster {src_cluster}")
        if item['name'] == target_cluster:
            logging.info(f"The update {'successful' if item['isDefault'] else 'unsuccessful'} for target cluster {target_cluster}")

    restart_service('domainmanager')

def update_edge_cluster(db_backup_path, src_cluster, target_cluster):
    """Update the edge cluster in the database."""
    take_database_dump(db_backup_path)
    response = execute_curl('clusters')

    src_cluster_id = next((item['id'] for item in response if item['name'] == src_cluster), "")
    target_cluster_id = next((item['id'] for item in response if item['name'] == target_cluster), "")

    logging.info(f"Source Cluster ID: {src_cluster_id}")
    logging.info(f"Destination Cluster ID: {target_cluster_id}")

    update_database(f"update cluster_and_nsxt_edge_cluster set cluster_id='{target_cluster_id}' where cluster_id='{src_cluster_id}';")

    response = execute_curl('nsxt-edgeclusters')
    if (item['clusterIds'] == target_cluster_id for item in response):
        logging.info(f"The update successful from source cluster {src_cluster} to target cluster {target_cluster}")
    else:
        logging.error(f"The update unsuccessful for source cluster {src_cluster} to target cluster {target_cluster}")

    restart_service('domainmanager')

def update_vcenter_datastore(db_backup_path, target_cluster):
    """Update the vCenter datastore in the database."""
    take_database_dump(db_backup_path)

    command = 'select count(*) AS vcentercount from VCENTER;'
    result = get_from_database(command)
    vcentercount = result[0]['vcentercount']

    response = execute_curl('clusters')
    target_cluster_datastore = next((item['primaryDatastoreName'] for item in response if item['name'] == target_cluster), "")

    logging.info(f"Destination datastore ID: {target_cluster_datastore}")

    update_database(f"update vcenter set datastore_name='{target_cluster_datastore}'")

    command = f"select count(*) AS updatecount from VCENTER where datastore_name='{target_cluster_datastore}';"
    result = get_from_database(command)
    updatecount = result[0]['updatecount']

    logging.info("Success" if vcentercount == updatecount else "Failure")

    restart_service('domainmanager')

def verify_domain(domain):
    """Verify if the workload domain exists."""
    return domain in get_domains_list()

def get_domains():
    """Get the list of workload domains."""
    return execute_curl('domains')

def get_domain_id_and_name():
    """Get a dictionary of workload domain names and their IDs."""
    return {domain['name']: domain['id'] for domain in get_domains()}

def get_domains_list():
    """Get a list of workload domain names."""
    return [domain['name'] for domain in get_domains()]

def get_domain_name_from_id(domain_id):
    """Get the domain name for a given workload domain ID."""
    return next((domain['name'] for domain in get_domains() if domain['id'] == domain_id), None)

def get_cluster_name_from_id(cluster_id):
    """Get the cluster name for a given cluster ID."""
    cluster = execute_curl(f'clusters/{cluster_id}')
    return cluster['name']

def get_clusters_list(domain_id):
    """Get a list of clusters for a given workload domain ID."""
    clusters_list = execute_curl('clusters')
    return [cluster_item['name'] for cluster_item in clusters_list if cluster_item['domainId'] == domain_id]

def verify_cluster(domain_id, cluster):
    """Verify if the cluster exists in the given workload domain."""
    return cluster in get_clusters_list(domain_id)

def get_user_input(prompt, verify_func, max_retries=2):
    """Get user input with verification and retry mechanism."""
    retry_count = max_retries
    while retry_count:
        user_input = input(prompt)
        if verify_func(user_input):
            return user_input
        logging.warning(f"Invalid input. Please try again. {retry_count - 1} attempts left.")
        retry_count -= 1
    logging.error("Maximum attempts reached. Exiting.")
    sys.exit(1)

if __name__ == "__main__":
    if getpass.getuser() != 'root':
        logging.error('Please execute this script as root user.')
        sys.exit(1)

    domain = get_user_input("Please enter the workload domain name: ", verify_domain)
    domain_hash = get_domain_id_and_name()
    domain_id = domain_hash[domain]

    src_cluster = get_user_input("Please enter the source cluster name: ", lambda x: verify_cluster(domain_id, x))
    target_cluster = get_user_input("Please enter the target cluster name: ", lambda x: verify_cluster(domain_id, x))

    menu = (
        "\nChoose from the following options as 1 or 2 or 3:\n"
        "1. Update the NSX Edge Cluster to vSphere cluster association in PSQL.\n"
        "2. Update the vCenter datastore association in PSQL.\n"
        "3. Update the workload domain default cluster in PSQL.\n"
    )
    option = int(input(menu))
    if option not in (1, 2, 3):
        logging.error("Invalid option. Choose the right option")
        sys.exit(1)

    match option:
        case 1:
            update_edge_cluster(BackupPaths.edge_cluster(timestamp), src_cluster, target_cluster)
        case 2:
            update_vcenter_datastore(BackupPaths.vcenter_datastore(timestamp), target_cluster)
        case 3:
            update_default_cluster(BackupPaths.default_cluster(timestamp), src_cluster, target_cluster)
