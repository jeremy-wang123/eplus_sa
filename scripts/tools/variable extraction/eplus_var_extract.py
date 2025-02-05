import os
import re
import csv
import glob

def convert_idf_to_txt(folder_path):
    """
    For every .idf file in the given folder, create a .txt copy.
    Returns a list of the new .txt file paths.
    """
    idf_files = glob.glob(os.path.join(folder_path, "*.idf"))
    txt_files = []
    for idf_file in idf_files:
        # Create a new filename with a .txt extension
        txt_file = os.path.splitext(idf_file)[0] + ".txt"
        with open(idf_file, 'r', encoding='utf-8') as infile:
            content = infile.read()
        with open(txt_file, 'w', encoding='utf-8') as outfile:
            outfile.write(content)
        txt_files.append(txt_file)
        print(f"Converted {idf_file} -> {txt_file}")
    return txt_files

def extract_heating_objects(txt_file):
    """
    Opens a .txt file (converted from an IDF), removes comments,
    and uses regex to extract objects that begin with "Coil:Heating:".
    Returns a list of dictionaries with the object type, object name,
    and a list of parameters.
    """
    # This regex pattern captures:
    #   - Group "obj_type": the object type (starting with Coil:Heating: and up to the first comma)
    #   - Group "fields": all text (including newlines) up to the terminating semicolon.
    pattern = re.compile(
        r"(?P<object>(?P<obj_type>Coil:Heating:[^,]+),\s*(?P<fields>.*?);)",
        re.DOTALL | re.IGNORECASE
    )
    
    with open(txt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove comments (anything after an exclamation mark on each line)
    content_no_comments = re.sub(r'!.*', '', content)

    heating_objects = []
    for match in pattern.finditer(content_no_comments):
        full_object = match.group("object")
        obj_type = match.group("obj_type").strip()
        fields = match.group("fields").strip()

        # Remove extra whitespace and newlines
        fields_clean = re.sub(r'\s+', ' ', fields)
        # Split by commas – each field is separated by a comma
        parameters = [param.strip() for param in fields_clean.split(',')]
        # Remove a trailing semicolon from the last parameter, if it exists
        if parameters and parameters[-1].endswith(';'):
            parameters[-1] = parameters[-1].rstrip(';').strip()
        # Assume that the first parameter in the fields is the object’s name
        obj_name = parameters[0] if parameters else ""
        
        heating_objects.append({
            "object_type": obj_type,
            "object_name": obj_name,
            "parameters": parameters
        })
    return heating_objects

def create_heating_dataset(folder_path, output_csv):
    """
    Process all IDF files in a folder: convert them to .txt files,
    then extract all heating objects and their parameters.
    Finally, output the aggregated data as a CSV file.
    """
    txt_files = convert_idf_to_txt(folder_path)
    all_objects = []

    for txt_file in txt_files:
        heating_objs = extract_heating_objects(txt_file)
        for obj in heating_objs:
            # Save the source file name along with the object data
            obj["source_file"] = os.path.basename(txt_file)
            all_objects.append(obj)
        print(f"Extracted {len(heating_objs)} heating objects from {txt_file}")

    # Write the dataset to a CSV file.
    # The "parameters" list is joined into one string separated by semicolons.
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["source_file", "object_type", "object_name", "parameters"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for obj in all_objects:
            writer.writerow({
                "source_file": obj["source_file"],
                "object_type": obj["object_type"],
                "object_name": obj["object_name"],
                "parameters": "; ".join(obj["parameters"])
            })
    print(f"Dataset created with {len(all_objects)} heating objects. Saved to {output_csv}")

# === Example usage ===
if __name__ == "__main__":
    # Set the folder containing your IDF files and the output CSV file path.
    folder_path = "data/ORNL Model America/NH_Grafton_IDF"      # <-- Change this to your folder path
    output_csv = "scripts/tools/variable extraction/heating_objects_dataset.csv"    # <-- Change output file name/path if desired
    create_heating_dataset(folder_path, output_csv)