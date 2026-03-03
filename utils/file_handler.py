import os
import pandas as pd
import json
from typing import Union
from werkzeug.utils import secure_filename
import csv

class FileHandler:
    def __init__(self):
        self.allowed_extensions = {'csv', 'xlsx', 'xls', 'json', 'txt'}
        self.upload_folder = 'uploads'
        self.result_folder = 'results'
        self.ensure_directories()

    def ensure_directories(self):
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)
        if not os.path.exists(self.result_folder):
            os.makedirs(self.result_folder)

    def allowed_file(self, filename: str) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    def read_file(self, path: str) -> pd.DataFrame:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        file_extension = path.rsplit('.', 1)[1].lower()
        try:
            if file_extension == 'csv':
                df = pd.read_csv(path, encoding='utf-8')
            elif file_extension in ['xlsx', 'xls']:
                df = pd.read_excel(path)
            elif file_extension == 'json':
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                elif isinstance(data, dict):
                    df = pd.DataFrame([data])
                else:
                    raise ValueError("Unsupported JSON format for DataFrame conversion")
            elif file_extension == 'txt':
                df = pd.read_csv(path, delimiter=' ')
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
            return df
        except Exception as e:
            raise ValueError(f"Error reading file {path}: {str(e)}")

    def save_file(self, data: pd.DataFrame, path: str) -> None:
        try:
            file_extension = path.rsplit('.', 1)[1].lower()
            if file_extension == 'csv':
                data.to_csv(path, index=False, encoding='utf-8')
            elif file_extension in ['xlsx', 'xls']:
                data.to_excel(path, index=False)
            elif file_extension == 'json':
                data.to_json(path, orient='records', indent=2, force_ascii=False)
            elif file_extension == 'txt':
                data.to_csv(path, sep=' ', index=False)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
        except Exception as e:
            raise ValueError(f"Error saving file {path}: {str(e)}")

    def upload_data(self, file) -> dict:
        if file and self.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(self.upload_folder, filename)
            file.save(file_path)
            return {'status': 'success', 'filepath': file_path}
        return {'status': 'error', 'message': 'Invalid file type'}

# Module level helpers to match imports in other files
file_handler = FileHandler()
def read_file(path: str) -> pd.DataFrame:
    return file_handler.read_file(path)

def save_file(data: pd.DataFrame, path: str) -> None:
    file_handler.save_file(data, path)