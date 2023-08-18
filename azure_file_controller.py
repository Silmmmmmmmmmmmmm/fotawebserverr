from io import BytesIO
import uuid
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobClient,BlobServiceClient
from django.conf import settings

from . import models


ALLOWED_EXTENTIONS = ['.pdf','.doc','.docx','.bin','.zip']

storage_account_key = "0e77Bl3w45EqddjDN0t23MK0d69vIi8BrqTQMjioUSVrJC9e+jloKmPQZqxslK9VZQd+KVLXQ84s+AStTJF47w=="
storage_account_name = "otastorage2"
connection_string = "DefaultEndpointsProtocol=https;AccountName=otastorage2;AccountKey=0e77Bl3w45EqddjDN0t23MK0d69vIi8BrqTQMjioUSVrJC9e+jloKmPQZqxslK9VZQd+KVLXQ84s+AStTJF47w==;EndpointSuffix=core.windows.net"
container_name = "otas"

def upload_to_blob_storage(file,file_name):
    print("in upload function to blob")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name,blob=file_name)
    blob_client.upload_blob(data=file)
    file_object = save_file_url_to_db(blob_client.url)
    return file_object


def check_file_ext(path):
    ext = Path(path).suffix
    return ext in ALLOWED_EXTENTIONS


def delete_file_blob(file_name):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)
    try:
        blob_client.delete_blob()
        return True
    except Exception as e:
        print("An error occurred:", str(e))
        return False
    

def save_file_url_to_db(file_url):
    new_file = models.File.objects.create(file_url=file_url)
    new_file.save()
    return new_file

def upload_file_to_blob(file):
    print("start")
    if not check_file_ext(file.name):
        return
    print("pass check file")
    file_prefix = str(file.name)
    ext = Path(file.name).suffix
    file_name = f"{file_prefix}"
    file_content = file.read()
    file_io = BytesIO(file_content)
    file_object = upload_to_blob_storage(file_io,file_name)
    print("end of line")
    return file_object

#List of packages
def list_blobs(): 
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container=container_name) 
    blob_list = container_client.list_blobs()
    print('file',blob_list)
    file_list= []
    for blob in blob_list:
        file_list.append(blob.name)
    return file_list

