#staging test file
import boto3
import os
import logging
import sys

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
from typing import List

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# session = boto3.Session(profile_name="devopsAdmin")
# s3 = session.client("s3")
s3 = boto3.client("s3")
bucket_name = "metro-cuadrado"
prefix = "Cleaned-Data/"


def shut_down_instance():
    region = "us-east-2"
    ec2_client = boto3.client("ec2", region_name=region)
    instance_ids = ["i-0559f52ef506ac0b8"]
    ec2_client.stop_instances(InstanceIds=instance_ids)


def get_diver():

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
    )
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def get_cleaned_files_names() -> List[str]:

    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    file_values = []

    bucket_objects = response.get("Contents", [])
    if bucket_objects:
        for obj in bucket_objects:
            file_name = obj["Key"].replace(prefix, "", 1)
            if file_name:
                file_values.append(file_name)
    return file_values


def delete_s3_file(file_key):
    """
    Delete a file from an S3 bucket.

    :param bucket_name: Name of the S3 bucket
    :param file_key: Key (path) of the file to delete
    :return: Response from the delete_object call
    """
    file_path = prefix + file_key
    try:
        response = s3.delete_object(Bucket=bucket_name, Key=file_path)
        return response
    except Exception as e:
        logging.error(f"Error deleting {file_key} from {bucket_name}: {e}")
        return None


def upload_to_s3(file_name: str, city: str, transaction_to_upload):
    upload_bucket = "metro-cuadrado-cleaned"
    uploadByteStream = bytes(json.dumps(transaction_to_upload).encode("UTF-8"))
    fileName = city.capitalize() + "/" + file_name + ".json"
    s3.put_object(Bucket=upload_bucket, Key=fileName, Body=uploadByteStream)


def get_params_data(driver):
    data = driver.find_element(By.ID, "__NEXT_DATA__")
    script_content = data.get_attribute("innerHTML")
    return script_content


def flatten_json(y):
    out = {}

    def flatten(x, name=""):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + "_")
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + "_")
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out


def save_as_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f)


def is_multiple_of_10(number):
    if number % 10 == 0:
        return True
    else:
        return False


def update_data(assets_list, driver, city, origin_name):
    iteration = 1
    for element in assets_list:
        logging.info(f"iteration {iteration}, sku: {element['product_sku']}")
        iteration = iteration + 1
        source = element["source"]
        try:
            driver.get(source)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//h1[@class='H1-xsrgru-0 jdfXCo mb-2 card-title']",
                    )
                )
            )
        except TimeoutException as err:
            logging.error(f"TimeoutException: {err}")
            continue
        except Exception as e:
            logging.error(f"Exception: {e}")
            continue
            # raise TimeoutError("Page not loaded") from err
        params_json = get_params_data(driver)
        json_string = json.loads(params_json)
        filtered_json = json_string["props"]["initialProps"]["pageProps"]["realEstate"]
        keys_to_remove = [
            "images",
            "breadcrumb",
            "backUrl",
            "titleSeo",
            "descriptionSeo",
            "linkSeo",
            "roomsFrom",
            "roomsTo",
            "bathroomsFrom",
            "bathroomsTo",
            "localPhone",
            "mcontactosucursalCelular1",
            "signwall",
            "campaign",
            "isOcasional",
            "isProject",
            "isUsed",
            "isSale",
            "isLease",
            "priceFrom",
            "priceUp",
            "fee",
            "areacFrom",
            "areacUp",
            "areaFrom",
            "areaUp",
            "video",
            "deliverDate",
            "featured",
            "companyId",
            "projectName",
            "salesRoomAddress",
            "companyName",
            "companyAddress",
            "companyImage",
            "companyLink",
            "companySeoUrl",
        ]
        for key in keys_to_remove:
            if key in filtered_json:
                del filtered_json[key]
        flattened_json = flatten_json(filtered_json)
        element.update(flattened_json)
        if is_multiple_of_10(iteration):
            process_data(city, assets_list, origin_name)
    return assets_list


def process_data(city_name: str, data_lis, origin_name: str):
    filename = f"{origin_name}"
    upload_to_s3(filename, city_name, data_lis)


def process_files(driver):
    all_files = get_cleaned_files_names()
    for file in all_files:
        file_name = file
        city_name = (file_name.split("_")[0]).capitalize()
        file_path = prefix + file_name

        s3.download_file(
            bucket_name,
            file_path,
            file_name,
        )

        with open(file_name, "r") as file:
            json_data = json.load(file)

        city_value = json_data.get("city").capitalize()
        initial_file_name = json_data.get("file")
        origin_file_name = initial_file_name.split("/")[2].split(".")[0]

        new_file_path = initial_file_name
        save_path = f"{origin_file_name}.json"
        s3.download_file(bucket_name, new_file_path, save_path)

        with open(save_path, "r") as file:
            json_data = json.load(file)
        final_data_list = update_data(json_data, driver, city_name, origin_file_name)

        process_data(city_name, final_data_list, origin_file_name)
        delete_s3_file(file_name)
        os.remove(save_path)
        os.remove(file_name)


chrome_driver = get_diver()
process_files(chrome_driver)
shut_down_instance()
