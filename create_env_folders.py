#!/usr/bin/env python

# Importing required modules
from    pb_vmware   import *
import  argparse
import  sys
import  getpass
import  time

# Start program
if __name__ == "__main__":
    # Parsing arguments
    parser = argparse.ArgumentParser(
        prog='create_env_folders.py'
    )
    parser.add_argument(
        '-p',
        '--password',
        help='vCenter password'
    )
    parser.add_argument(
        '-s',
        '--server',
        help='vCenter server name or IP address',
        required=True
    )
    parser.add_argument(
        '-u',
        '--username',
        help='vCenter username',
        required=True
    )
    parser.add_argument(
        '-v',
        '--verbose',
        help='more information displayed',
        action='store_true'
    )
    args = parser.parse_args()
    # General arguments
    verbose         =   args.verbose
    # Arguments for connecting to the vCenter
    hostname        =   args.server
    username        =   args.username
    passwd          =   args.password

    # Asking user for password if not specified on the commandline
    if passwd is None:
        passwd  =   getpass.getpass()

    # Connecting
    print "Connecting to '%s' as user '%s'..." % (hostname, username)
    instance, content, datacenters, datacenter, vm_folder = vcenter_connect(
        hostname,
        username,
        passwd
    )

    # Our environments
    envs =  [
            'custenv01', 'custenv02', 'custenv03', 'custenv04', 'custenv05',
            'custenv06', 'custenv07', 'custenv08', 'custenv09', 'custenv30'
            ]
    variants = ['prd','sbx']

    parent_folder_name = 'acme'
    parent_folder = get_obj(content, 'folder', parent_folder_name)

    for env in envs:
        for variant in variants:
            folder_name = 'acme-{0}-{1}'.format(env, variant)
            create_folder(content, parent_folder, folder_name)
            time.sleep(5)

    # Clean exit
    vcenter_disconnect(instance)
    sys.exit(0)
