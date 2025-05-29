FROM python:3.7-alpine

# update apk repo
RUN echo "http://dl-4.alpinelinux.org/alpine/v3.14/main" >> /etc/apk/repositories && \
    echo "http://dl-4.alpinelinux.org/alpine/v3.14/community" >> /etc/apk/repositories

RUN apk update
RUN apk add chromium chromium-chromedriver
RUN apk add xvfb

# upgrade pip
RUN pip install --upgrade pip

COPY requirements-selenium.txt .
RUN pip install -r requirements-selenium.txt

COPY get_full_data.py ./
# COPY chromedriver ./
# COPY headless-chromium ./

# ENTRYPOINT ["tail", "-f", "/dev/null"]
CMD ["python", "get_full_data.py"]