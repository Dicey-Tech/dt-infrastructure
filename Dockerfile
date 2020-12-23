FROM pulumi/pulumi-python

COPY requirements.txt /pulumi/projects/

RUN pip3 install -r requirements.txt