from ultralytics import YOLO
import os
import shutil
import random
import yaml
import zipfile

ZIP_FILE = "dataset.zip"
# ----------------

if os.path.exists("temp_raw"):
    shutil.rmtree("temp_raw")
    
zipfile.ZipFile(ZIP_FILE, 'r').extractall("temp_raw")

classes_file_path = None
CLASSES = []

for root, _, files in os.walk("temp_raw"):
    if "classes.txt" in files:
        classes_file_path = os.path.join(root, "classes.txt")
        break

if classes_file_path:
    with open(classes_file_path, 'r') as f:
        CLASSES = [line.strip() for line in f.readlines() if line.strip()]
    print(f"✅ Successfully read classes file！{len(CLASSES)} classes detected: {CLASSES}")
else:
    print("❌ No classes.txt are found in zip file！")
    print("Please ensure student zip the file with classes.txt")

base_dir = "/content/my_yolo_dataset"
if os.path.exists(base_dir):
    shutil.rmtree(base_dir)

dirs = {
    'train': os.path.join(base_dir, 'train'),
    'val': os.path.join(base_dir, 'val')
}
for d in dirs.values():
    os.makedirs(os.path.join(d, 'images'), exist_ok=True)
    os.makedirs(os.path.join(d, 'labels'), exist_ok=True)

all_files = []
for root, _, files in os.walk("temp_raw"):
    for file in files:
        if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            img_path = os.path.join(root, file)
            txt_path = os.path.splitext(img_path)[0] + ".txt"

            if os.path.exists(txt_path):
                all_files.append({'img': img_path, 'txt': txt_path})

print(f"{len(all_files)} set of valid data(image + txt) found")

random.shuffle(all_files)
split_idx = int(len(all_files) * 0.8) # 80% 訓練
train_data = all_files[:split_idx]
val_data = all_files[split_idx:]

def move_data(data_list, split_type):
    for item in data_list:
        file_name = os.path.basename(item['img'])
        shutil.copy(item['img'], f"{dirs[split_type]}/images/{file_name}")
        shutil.copy(item['txt'], f"{dirs[split_type]}/labels/{os.path.splitext(file_name)[0]}.txt")

move_data(train_data, 'train')
move_data(val_data, 'val')

yaml_content = {
    'path': base_dir,
    'train': 'train/images',
    'val': 'val/images',
    'nc': len(CLASSES),
    'names': CLASSES
}

with open(f"{base_dir}/data.yaml", 'w') as f:
    yaml.dump(yaml_content, f, sort_keys=False)

print("✅ data.yaml generated, ready for traning！")