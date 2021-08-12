#!/usr/bin/env
 
import datetime
import json
import os
import re
import fnmatch
from PIL import Image
import numpy as np
from pycococreatortools import pycococreatortools
 
# 这里设置一些文件路径
ROOT_DIR = 'data/coco' # 根目录
IMAGE_DIR = os.path.join(ROOT_DIR, "test") # 根目录下存放你原图的文件夹
# ANNOTATION_DIR = os.path.join(ROOT_DIR, "annotations") # 根目录下存放mask标签的文件夹
 
# 这里就是填一些有关你数据集的信息
# INFO = {
#     "description": "Example Dataset",
#     "url": "https://github.com/waspinator/pycococreator",
#     "version": "0.1.0",
#     "year": 2018,
#     "contributor": "waspinator",
#     "date_created": datetime.datetime.utcnow().isoformat(' ')
# }
 
# LICENSES = [
#     {
#         "id": 1,
#         "name": "Attribution-NonCommercial-ShareAlike License",
#         "url": "http://creativecommons.org/licenses/by-nc-sa/2.0/"
#     }
# ]
 
# 这里是你数据集的类别，这里有三个分类，就是square, circle, triangle。制作自己的数据集主要改这里就行了
CATEGORIES = [
        {
            "supercategory": "none",
            "id": 1,
            "name": "knife"
        },
        {
            "supercategory": "none",
            "id": 2,
            "name": "scissors"
        },
        {
            "supercategory": "none",
            "id": 3,
            "name": "sharpTools"
        },
        {
            "supercategory": "none",
            "id": 4,
            "name": "expandableBaton"
        },
        {
            "supercategory": "none",
            "id": 5,
            "name": "smallGlassBottle"
        },
        {
            "supercategory": "none",
            "id": 6,
            "name": "electricBaton"
        },
        {
            "supercategory": "none",
            "id": 7,
            "name": "plasticBeverageBottle"
        },
        {
            "supercategory": "none",
            "id": 8,
            "name": "plasticBottleWithaNozzle"
        },
        {
            "supercategory": "none",
            "id": 9,
            "name": "electronicEquipment"
        },
        {
            "supercategory": "none",
            "id": 10,
            "name": "battery"
        },
        {
            "supercategory": "none",
            "id": 11,
            "name": "seal"
        },
        {
            "supercategory": "none",
            "id": 12,
            "name": "umbrella"
        }
]
 
def filter_for_jpeg(root, files):
    file_types = ['*.jpeg', '*.jpg']
    file_types = r'|'.join([fnmatch.translate(x) for x in file_types])
    files = [os.path.join(root, f) for f in files]
    files = [f for f in files if re.match(file_types, f)]
    
    return files
 
def filter_for_annotations(root, files, image_filename):
    file_types = ['*.png']
    file_types = r'|'.join([fnmatch.translate(x) for x in file_types])
    basename_no_extension = os.path.splitext(os.path.basename(image_filename))[0]
    file_name_prefix = basename_no_extension + '.*'
    files = [os.path.join(root, f) for f in files]
    files = [f for f in files if re.match(file_types, f)]
    files = [f for f in files if re.match(file_name_prefix, os.path.splitext(os.path.basename(f))[0])]
 
    return files
 
def main():
 
    coco_output = {
        "images": [],
        "annotations": [],
        "categories": CATEGORIES
    }
 
    image_id = 1

    
    # filter for jpeg images

    image_files = os.listdir(IMAGE_DIR)
    image_files.sort()
 
        # go through each image
    for image_filename in image_files:
        image = Image.open(os.path.join(IMAGE_DIR, image_filename))
        image_info = pycococreatortools.create_image_info(
            image_id, os.path.basename(image_filename), image.size)
        coco_output["images"].append(image_info)
        image_id = image_id + 1
 
    with open('{}/coco_test1.json'.format(ROOT_DIR), 'w') as output_json_file:
        json.dump(coco_output, output_json_file, indent=4)
 
 
if __name__ == "__main__":
    main()