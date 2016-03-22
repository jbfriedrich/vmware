#!/usr/bin/env python

# Importing required modules
from pb_vmware import *
import argparse
import sys
import getpass

# Start program
if __name__ == "__main__":
    # Parsing arguments
    parser = argparse.ArgumentParser(
        prog='create_vm_from_template.py'
    )
    parser.add_argument(
        '-c',
        '--cluster',
        type=str,
        help='Target HA/DRS cluster'
    )
    parser.add_argument(
        '-d',
        '--destination',
        type=str,
        help='Destination VM',
        required=True
    )
    parser.add_argument(
        '-f',
        '--folder',
        type=str,
        help='Destination folder'
    )
    parser.add_argument(
        '-o',
        '--datastore',
        type=str,
        help='Target datastore or datastore cluster',
        default='datastore1'
    )
    parser.add_argument(
        '-p',
        '--password',
        help='vCenter password'
    )
    parser.add_argument(
        '-r',
        '--resourcepool',
        type=str,
        help='Resource pool the VM should be placed in',
        default='Resources'
    )
    parser.add_argument(
        '-s',
        '--server',
        help='vCenter server name or IP address',
        required=True
    )
    parser.add_argument(
        '-t',
        '--template',
        help='Source template to clone from',
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
    # Arguments for cloning VMs from template
    folder_name     =   args.folder
    template_name   =   args.template
    target_name     =   args.destination
    resourcepool    =   args.resourcepool
    datastore       =   args.datastore
    cluster         =   args.cluster
    # Asking user for password if not specified on the commandline
    if passwd is None:
        passwd  =   getpass.getpass()

    print "Connecting to '%s' as user '%s'..." % (hostname, username)
    instance, content, datacenters, datacenter, vm_folder = vcenter_connect(
        hostname,
        username,
        passwd
    )

    template_vm     =   get_obj(content, 'template', template_name)

    if (check_if_template(template_vm) is not True):
        print 'Specified template is no VMware template'
        vcenter_disconnect(instance)
        sys.exit(1)
    else:
        print "Template '%s' found (%s)" % (template_name, template_vm)

    # If there is no argument specified for the cluster, we search for the object
    if cluster is None:
        ha_cluster      =   get_obj(content, 'cluster', cluster)
    else:
        ha_cluster      =   cluster

    resource_pool   =   get_obj(content, 'respool', resourcepool)
    data_store      =   get_obj(content, 'datastore', datastore)

    # If no folder name argument was given, we assume root folder
    if folder_name is None:
        folder = vm_folder
    else:
        create_folder(content, vm_folder, folder_name)
        folder = get_obj(content, 'folder', folder_name)

    clone_vm(template_vm, target_name, folder, data_store, resource_pool)
    # Clean exit
    vcenter_disconnect(instance)
    sys.exit(0)
