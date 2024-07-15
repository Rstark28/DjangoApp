import os
import shutil
import fileinput

def rename_files_and_directories(root_dir, old_name, new_name):
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        for name in filenames:
            if name == old_name:
                old_path = os.path.join(dirpath, name)
                new_path = os.path.join(dirpath, new_name)
                os.rename(old_path, new_path)
        for name in dirnames:
            if name == old_name:
                old_path = os.path.join(dirpath, name)
                new_path = os.path.join(dirpath, new_name)
                os.rename(old_path, new_path)

def replace_text_in_files(root_dir, old_text, new_text):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for name in filenames:
            file_path = os.path.join(dirpath, name)
            try:
                with open(file_path, 'r+', encoding='utf-8') as file:
                    content = file.read()
                    new_content = content.replace(old_text, new_text)
                    if new_content != content:
                        file.seek(0)
                        file.write(new_content)
                        file.truncate()
            except Exception as e:
                # Skip non-text files
                continue

def main():
    root_dir = os.getcwd()  # Use the current directory
    old_name = 'main'
    new_name = 'main'

    rename_files_and_directories(root_dir, old_name, new_name)
    replace_text_in_files(root_dir, old_name, new_name)

if __name__ == '__main__':
    main()
