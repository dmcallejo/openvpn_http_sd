from python:3-alpine


WORKDIR /opt/openvpn_http_sd

COPY requirements.txt .

RUN pip3 install -r requirements.txt

COPY openvpn_http_sd.py .

ENTRYPOINT ["./openvpn_http_sd.py"]
