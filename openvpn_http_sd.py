#!/usr/bin/env python3

import logging

import toml
from aiohttp import web
import argparse
import os
import ipaddress


routes = web.RouteTableDef()
LOG = logging.getLogger()

OPENVPN_PATH = '/etc/openvpn/server/'
OPENVPN_FILES = []
CONF_FILE = '/etc/openvpn_http_sd.toml'
CONF = {}
IGNORED_HOSTS = []


def find_log_files(directory):
    log_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".log"):
                log_files.append(os.path.join(root, file))
    return log_files


def read_conf_file(file_path):
    try:
        with open(file_path, 'r') as f:

            conf = toml.load(f)
            for host_name in conf['hosts']:
                host = conf['hosts'][host_name]
                if "ip_ranges" in host:
                    new_ip_ranges = []
                    for ip_range in host['ip_ranges']:
                        new_ip_ranges.append(ipaddress.ip_network(ip_range))
                    conf['hosts'][host_name]['ip_ranges'] = new_ip_ranges
                if "ignored" in host:
                    for address in host['ignored']:
                        IGNORED_HOSTS.append(address)
    except FileNotFoundError:
        # Return an empty list if the file doesn't exist
        conf = {}
    return conf


@routes.get('/')
async def discover(request):
    data = []
    if len(OPENVPN_FILES) == 0:
        log_files = find_log_files(OPENVPN_PATH)
    else:
        log_files = OPENVPN_FILES

    for log_file in log_files:
        data.append(parse_file(log_file))

    return web.json_response(data)


def parse_file(filepath):
    # Initialize the list of virtual addresses
    virtual_addresses = []
    labels = {}
    with open(filepath, 'r') as file:
        for line in file:
            # Split the line into components
            parts = line.strip().split(',')
            if parts[0] == "TITLE":
                labels["__meta_openvpn"] = parts[1]
            if parts[0] == "TIME":
                labels["__meta_time"] = parts[1]
            # Check if the line is a CLIENT_LIST line
            if parts[0] == "CLIENT_LIST":
                # Extract the virtual address and add it to the list
                client_data = parse_client_line(parts)
                if client_data:
                    client_data['labels'] = client_data['labels'] | labels
                    virtual_addresses.append(client_data)
                else:
                    continue

    return virtual_addresses


def parse_client_line(client_line_parts: list):
    virtual_address = client_line_parts[3]
    if virtual_address in IGNORED_HOSTS:
        return None
    label_name = client_line_parts[1]
    public_ip = client_line_parts[2].split(':')[0]
    for host_name in CONF['hosts']:
        host = CONF['hosts'][host_name]
        if "ip_ranges" in host:
            for ip_range in host['ip_ranges']:
                if ipaddress.ip_address(virtual_address) in ip_range:
                    targets = []
                    for port in host['ports']:
                        targets.append(f"{virtual_address}:{port}")
                    data = {
                        "targets": targets,
                        "labels": {
                            "__meta_public_ip": public_ip,
                            "group": host_name,
                            "name": label_name
                        }
                    }
                    return data


@routes.get('/healthz')
@routes.get('/healthcheck')
async def healthcheck(request):
    return web.Response(text="OK.")


def setup_logger(log_level):
    """
    Sets a rotating file and console stdout log
    """
    LOG.setLevel(log_level)

    # add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    LOG.addHandler(console_handler)

    logger = logging.getLogger("openvpn_http_sd")

    return logger


def create_arg_parser():
    argparser = argparse.ArgumentParser(description='HTTP Service Discovery for OpenVPN')

    # Arguments for one or more paths for "openvpn status file"
    argparser.add_argument('--status-files', nargs='+', required=False,
                           default=os.environ.get('STATUS_FILES', '').split(),
                           help='Paths to OpenVPN status files')

    # Argument for one path for openvpn status path
    argparser.add_argument('--status-path', required=False,
                           default=os.environ.get('STATUS_PATH', OPENVPN_PATH),
                           help=f'Path for OpenVPN status file path. Defaults to {OPENVPN_PATH}')

    # Argument for one path for openvpn ignore hosts file
    argparser.add_argument('--conf-file', required=False,
                           default=os.environ.get('CONF_FILE', CONF_FILE),
                           help=f'Path for app config file. Defaults to {CONF_FILE}')

    # Argument for log verbosity modifier
    argparser.add_argument('--log-verbosity', type=str, required=False,
                           default=os.environ.get('LOG_VERBOSITY', 'INFO'),
                           help='Log verbosity modifier')

    # Argument for webserver port
    argparser.add_argument('--webserver-port', type=int, required=False,
                           default=os.environ.get('WEBSERVER_PORT', 8080),
                           help='Port for the webserver')

    # Argument for webserver host
    argparser.add_argument('--webserver-host', required=False,
                           default=os.environ.get('WEBSERVER_HOST', '0.0.0.0'),
                           help='Host for the webserver')

    return argparser


if __name__ == '__main__':
    parser = create_arg_parser()
    args = parser.parse_args()
    LOG = setup_logger(logging.getLevelName(args.log_verbosity))

    LOG.debug(f"Status Files: {args.status_files}")
    LOG.debug(f"Status Path: {args.status_path}")
    LOG.debug(f"Conf file: {args.conf_file}")
    LOG.debug(f"Log Verbosity: {args.log_verbosity}")
    LOG.debug(f"Webserver Port:{args.webserver_port}")
    LOG.debug(f"Webserver Host: {args.webserver_host}")

    if len(args.status_files) == 0:
        OPENVPN_PATH = args.status_path
        LOG.info(f"Watching {OPENVPN_PATH} for openvpn-status files.")
    else:
        OPENVPN_FILES = args.status_files
        LOG.info(f"Watching {OPENVPN_FILES} for changes.")

    CONF = read_conf_file(args.conf_file)

    app = web.Application(logger=LOG.getChild("aiohttp"))
    app.add_routes(routes)
    web.run_app(app, host=args.webserver_host, port=args.webserver_port)
