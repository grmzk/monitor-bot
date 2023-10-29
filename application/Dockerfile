FROM python:3.10-bookworm

WORKDIR /app

COPY ./requirements.txt .
RUN pip3 install pip --upgrade --no-cache-dir
RUN pip3 install -r requirements.txt --no-cache-dir

COPY ./ .
RUN dpkg -i extra_files/libfbclient-2.1.3/*.deb

CMD ["python3", "main.py"]