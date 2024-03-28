# openvpn_http_sd

## HTTP Service Discovery application for OpenVPN

An application quickly hacked together to obtain all the clients connected to a vpn in service discovery format for Prometheus using the openvpn-status file.

```commandline
usage: openvpn_http_sd.py [-h] [--status-files STATUS_FILES [STATUS_FILES ...]] [--status-path STATUS_PATH] [--ports PORTS [PORTS ...]] [--log-verbosity LOG_VERBOSITY] [--webserver-port WEBSERVER_PORT] [--webserver-host WEBSERVER_HOST]

HTTP Service Discovery for OpenVPN

options:
  -h, --help            show this help message and exit
  --status-files STATUS_FILES [STATUS_FILES ...]
                        Paths to OpenVPN status files
  --status-path STATUS_PATH
                        Path for OpenVPN status file path. Defaults to /etc/openvpn/server/
  --ports PORTS [PORTS ...]
                        Ports for targets. Defaults to 9100
  --log-verbosity LOG_VERBOSITY
                        Log verbosity modifier
  --webserver-port WEBSERVER_PORT
                        Port for the webserver
  --webserver-host WEBSERVER_HOST
                        Host for the webserver
```
