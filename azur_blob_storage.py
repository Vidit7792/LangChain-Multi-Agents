from azure.storage.blob import BlobServiceClient
import pickle, datetime, logging, os

# Azure storage account connection string
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", None)

# Create a BlobServiceClient object
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Name of the container
container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", None)

# Create a container client
container_client = blob_service_client.get_container_client(container_name)

# Upload a file to the container
def upload_file_to_blob(transaction_id, data_obj, user_name=None, user_id=None):
    try:
        # Create a blob client using the local file name as the blob name
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=transaction_id+'.pkl')

        pickled_data = pickle.dumps(data_obj)

        logging.info(f"Uploading file to Azure Storage as blob {transaction_id}.pkl")

        #create metadata for file
        try:
            metadata = {'transaction_id': transaction_id, 'user_name': data_obj.name, 'user_id': data_obj.user_id,
                        'updated_at': str(datetime.datetime.now())}
        except Exception as _:
            metadata = {'transaction_id': transaction_id, 'updated_at': str(datetime.datetime.now())}

        # Upload the file
        blob_client.upload_blob(pickled_data, metadata=metadata, overwrite=True)

        logging.info(f"Upload successful {transaction_id}.pkl")
    
    except Exception as ex:
        logging.error(f"Exception occurred: {ex}")


# Download a file from the container
def download_file_from_blob(file_path):
    try:
        # Create a blob client
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_path)
        
        logging.info(f"Downloading blob {file_path}")
        
        # Download the file
        download_data = blob_client.download_blob()

        logging.info("Download successful!")

        return pickle.loads(download_data.readall())
    
    
    except Exception as ex:
        logging.error(f"Exception occurred while downloading file from storgae: {ex}")
        return None
