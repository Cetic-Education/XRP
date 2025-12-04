import os
import shutil
import random
import math

# ================= setting area =================
# Source directory (relative path, pointing to the img folder at the same level as the script)
SOURCE_DIR = './img'

# Output directory (will be created automatically, e.g., output_task)
OUTPUT_BASE_DIR = './output_task'

# How many people do you want to distribute to?
NUM_PEOPLE = 3 
# ===========================================

def distribute_images():
    # 1. Check if source directory exists
    if not os.path.exists(SOURCE_DIR):
        print(f"Error: '{SOURCE_DIR}' directory not found in the current directory.")
        print(f"Please make sure the script is at the same level as the img directory.")
        return

    # 2. Get the list of images
    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff')
    all_files = [
        f for f in os.listdir(SOURCE_DIR) 
        if f.lower().endswith(valid_extensions) and os.path.isfile(os.path.join(SOURCE_DIR, f))
    ]
    
    total_files = len(all_files)
    if total_files == 0:
        print(f"No images found in '{SOURCE_DIR}'.")
        return

    print(f"--- Starting process ---")
    print(f"Source: {SOURCE_DIR}")
    print(f"Total images: {total_files}")
    print(f"Number of people to distribute to: {NUM_PEOPLE}")

    # 3. Random shuffle
    random.shuffle(all_files)

    # 4. Calculate how many per person (round up to ensure all are distributed)
    files_per_person = math.ceil(total_files / NUM_PEOPLE)

    # 5. Clean or create output directory
    if os.path.exists(OUTPUT_BASE_DIR):
        print(f"Note: Output directory '{OUTPUT_BASE_DIR}' already exists. New files will be written into it.")
    else:
        os.makedirs(OUTPUT_BASE_DIR)

    # 6. Start distributing and copying
    global_counter = 1  # Global serial number, starting from 000001

    for i in range(NUM_PEOPLE):
        # Create individual folder, e.g., person_1
        person_dir_name = f"person_{i+1}"
        person_full_path = os.path.join(OUTPUT_BASE_DIR, person_dir_name)
        os.makedirs(person_full_path, exist_ok=True)

        # Slice out this batch of images
        start_idx = i * files_per_person
        end_idx = start_idx + files_per_person
        batch = all_files[start_idx:end_idx]

        if not batch:
            break

        print(f"Distributing to {person_dir_name}: {len(batch)} images...")

        for filename in batch:
            # Get file extension
            _, ext = os.path.splitext(filename)
            
            # Rename: 000001.jpg, 000002.png ...
            new_name = f"{global_counter:06d}{ext}"
            
            src_file = os.path.join(SOURCE_DIR, filename)
            dst_file = os.path.join(person_full_path, new_name)
            
            # Copy file
            shutil.copy2(src_file, dst_file)
            
            global_counter += 1

    print("---")
    print(f"Success! Please check the '{OUTPUT_BASE_DIR}' directory.")

if __name__ == "__main__":
    distribute_images()