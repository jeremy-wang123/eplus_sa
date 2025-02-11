import os
import re
import csv
import glob
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

def convert_idf_file(idf_file, txt_folder):
    """
    Reads an IDF file and writes its content to a corresponding TXT file.
    Returns the path of the new TXT file.
    """
    base_name = os.path.splitext(os.path.basename(idf_file))[0]
    txt_file = os.path.join(txt_folder, base_name + ".txt")
    with open(idf_file, 'r', encoding='utf-8') as infile:
        content = infile.read()
    with open(txt_file, 'w', encoding='utf-8') as outfile:
        outfile.write(content)
    print(f"Converted {idf_file} -> {txt_file}")
    return txt_file

def convert_idf_to_txt(folder_path):
    """
    Converts every .idf file in folder_path to a .txt file in a subfolder "txt".
    This version uses a ThreadPoolExecutor to process files concurrently.
    Returns the list of new TXT file paths.
    """
    txt_folder = os.path.join(folder_path, "txt")
    if not os.path.exists(txt_folder):
        os.makedirs(txt_folder)
        print(f"Created folder: {txt_folder}")

    idf_files = glob.glob(os.path.join(folder_path, "*.idf"))
    txt_files = []

    with ThreadPoolExecutor() as executor:
        # Submit all conversion tasks concurrently.
        futures = [executor.submit(convert_idf_file, idf_file, txt_folder)
                   for idf_file in idf_files]
        for future in as_completed(futures):
            txt_files.append(future.result())

    return txt_files

def extract_heating_objects_from_file(txt_file):
    """
    Opens a TXT file (converted from an IDF), removes comments,
    and uses a regex to extract objects that begin with "Coil:Heating:".
    Objects whose type contains "equationfit" are excluded via the regex itself.
    
    Returns a list of dictionaries containing:
      - the source file name (and the numbers before the .txt extension as file_number)
      - the object type
      - the object name, and
      - the list of parameters.
    """
    # The regex does the following:
    # - Matches a literal "Coil:Heating:".
    # - Uses a negative lookahead (?![^,]*equationfit) to ensure that in the
    #   following non-comma characters, the substring "equationfit" does not appear.
    # - Then it matches the rest of the object type (until the comma) and the fields (until the semicolon).
    pattern = re.compile(
        r"(?P<object>(?P<obj_type>Coil:Heating:(?![^,]*equationfit)[^,]+),\s*(?P<fields>.*?);)",
        re.DOTALL | re.IGNORECASE
    )
    
    with open(txt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove comments: anything after an exclamation mark on each line.
    content_no_comments = re.sub(r'!.*', '', content)

    heating_objects = []
    source_file = os.path.basename(txt_file)
    # Extract the numbers just before the .txt extension.
    file_number_match = re.search(r'(\d+)(?=\.txt$)', source_file)
    file_number = file_number_match.group(1) if file_number_match else ""

    for match in pattern.finditer(content_no_comments):
        fields = match.group("fields").strip()

        # Normalize whitespace and split the parameters by comma.
        fields_clean = re.sub(r'\s+', ' ', fields)
        parameters = [param.strip() for param in fields_clean.split(',') if param.strip()]
        # Remove a trailing semicolon in the last parameter, if present.
        if parameters and parameters[-1].endswith(';'):
            parameters[-1] = parameters[-1].rstrip(';').strip()
        # Assume the first parameter is the object name.
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
    """
    Processes all IDF files in folder_path by:
      1. Converting them to TXT files (parallelized)
      2. Extracting heating objects from each TXT file (parallelized)
      3. Aggregating the data into a CSV file.
    """
    # Step 1: Convert IDF files to TXT files concurrently.
    txt_files = convert_idf_to_txt(folder_path)
    all_objects = []

    # Step 2: Use a ProcessPoolExecutor for extraction (good for CPU-bound regex work).
    with ProcessPoolExecutor() as executor:
        future_to_file = {executor.submit(extract_heating_objects_from_file, txt_file): txt_file
                          for txt_file in txt_files}
        for future in as_completed(future_to_file):
            try:
                objs = future.result()
                all_objects.extend(objs)
            except Exception as e:
                print(f"Error processing {future_to_file[future]}: {e}")

    # Step 3: Write the aggregated data to a CSV file.
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

# === Example usage ===
if __name__ == "__main__":
    # Set the folder containing your IDF files and the output CSV file path.
    folder_path = "data/ORNL Model America/NH_Grafton_IDF"  # <-- Adjust to your folder
    output_csv = "scripts/tools/variable extraction/heating_objects_dataset.csv"           
    create_heating_dataset(folder_path, output_csv)