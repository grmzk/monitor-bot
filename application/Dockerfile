FROM python:3.12-bookworm

WORKDIR /app

RUN ln -sf /usr/share/zoneinfo/Asia/Omsk /etc/localtime

COPY ./requirements.txt .
RUN pip3 install pip --upgrade --no-cache-dir
RUN pip3 install -r requirements.txt --no-cache-dir

COPY ./ .
RUN dpkg -i extra_files/libfbclient-2.1.3/*.deb

CMD ["python3", "main.py"]