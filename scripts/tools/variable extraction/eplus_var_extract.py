import os
import re
import csv
import glob
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

def convert_idf_file(idf_file, txt_folder):
    base_name = os.path.splitext(os.path.basename(idf_file))[0]
    txt_file = os.path.join(txt_folder, base_name + ".txt")
    with open(idf_file, 'r', encoding='utf-8') as infile:
        content = infile.read()
    with open(txt_file, 'w', encoding='utf-8') as outfile:
        outfile.write(content)
    print(f"Converted {idf_file} -> {txt_file}")
    return txt_file

def convert_idf_to_txt(folder_path):
    txt_folder = os.path.join(folder_path, "txt")
    if not os.path.exists(txt_folder):
        os.makedirs(txt_folder)
        print(f"Created folder: {txt_folder}")
    idf_files = glob.glob(os.path.join(folder_path, "*.idf"))
    txt_files = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(convert_idf_file, idf_file, txt_folder) for idf_file in idf_files]
        for future in as_completed(futures):
            txt_files.append(future.result())
    return txt_files

def extract_heating_objects_from_file(txt_file):
    pattern = re.compile(
        r"(?P<object>(?P<obj_type>Coil:Heating:(?![^,]*equationfit)[^,]+),\s*(?P<fields>.*?);)",
        re.DOTALL | re.IGNORECASE
    )
    with open(txt_file, 'r', encoding='utf-8') as f:
        content = f.read()
    content_no_comments = re.sub(r'!.*', '', content)
    heating_objects = []
    source_file = os.path.basename(txt_file)
    file_number_match = re.search(r'(\d+)(?=\.txt$)', source_file)
    file_number = file_number_match.group(1) if file_number_match else ""
    for match in pattern.finditer(content_no_comments):
        fields = match.group("fields").strip()
        fields_clean = re.sub(r'\s+', ' ', fields)
        parameters = [param.strip() for param in fields_clean.split(',') if param.strip()]
        if parameters and parameters[-1].endswith(';'):
            parameters[-1] = parameters[-1].rstrip(';').strip()
        obj_name = parameters[0] if parameters else ""
        heating_objects.append({
            "source_file": source_file,
            "file_number": file_number,
            "object_type": match.group("obj_type").strip(),
            "object_name": obj_name,
            "parameters": parameters
        })
    print(f"Extracted {len(heating_objects)} heating objects from {txt_file}")
    return heating_objects

def create_heating_dataset(folder_path, output_csv):
    txt_files = convert_idf_to_txt(folder_path)
    all_objects = []
    with ProcessPoolExecutor() as executor:
        future_to_file = {executor.submit(extract_heating_objects_from_file, txt_file): txt_file for txt_file in txt_files}
        for future in as_completed(future_to_file):
            try:
                objs = future.result()
                all_objects.extend(objs)
            except Exception as e:
                print(f"Error processing {future_to_file[future]}: {e}")
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["source_file", "file_number", "object_type", "object_name", "parameters"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for obj in all_objects:
            writer.writerow({
                "source_file": obj["source_file"],
                "file_number": obj["file_number"],
                "object_type": obj["object_type"],
                "object_name": obj["object_name"],
                "parameters": "; ".join(obj["parameters"])
            })
    print(f"Dataset created with {len(all_objects)} heating objects. Saved to {output_csv}")

if __name__ == "__main__":
    folder_path = "data/ORNL Model America/NH_Grafton_IDF"
    output_csv = "scripts/tools/variable extraction/heating_objects_dataset.csv"
    create_heating_dataset(folder_path, output_csv)
