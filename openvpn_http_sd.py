#!/usr/bin/env python3

import logging

from aiohttp import web
import argparse
import os


routes = web.RouteTableDef()
LOG = logging.getLogger()

OPENVPN_PATH = '/etc/openvpn/server/'
OPENVPN_FILES = []
TARGET_PORTS = ['9100']


def find_log_files(directory):
    log_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".log"):
                log_files.append(os.path.join(root, file))
    return log_files


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
                virtual_address = parts[3]
                if virtual_address:  # Ensure the address is not empty
                    for port in TARGET_PORTS:
                        virtual_addresses.append(f"{virtual_address}:{port}")

    # Create a JSON structure
    data = {
        "targets": virtual_addresses,
        "labels": labels
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

    # Argument for one or more ports for "targets"
    argparser.add_argument('--ports', nargs='+', required=False,
                           default=os.environ.get('PORTS', '9100').split(),
                           help='Ports for targets. Defaults to 9100')

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
    LOG.debug(f"Ports: {args.ports}")
    LOG.debug(f"Log Verbosity: {args.log_verbosity}")
    LOG.debug(f"Webserver Port:{args.webserver_port}")
    LOG.debug(f"Webserver Host: {args.webserver_host}")

    if len(args.status_files) == 0:
        OPENVPN_PATH = args.status_path
        LOG.info(f"Watching {OPENVPN_PATH} for openvpn-status files.")
    else:
        OPENVPN_FILES = args.status_files
        LOG.info(f"Watching {OPENVPN_FILES} for changes.")

    TARGET_PORTS = args.ports

    app = web.Application(logger=LOG.getChild("aiohttp"))
    app.add_routes(routes)
    web.run_app(app, host=args.webserver_host, port=args.webserver_port)
