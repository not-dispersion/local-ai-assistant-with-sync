import os
import json
from typing import List, Dict
from sklearn.metrics.pairwise import cosine_similarity
import ollama

class FileHandler:
    def __init__(self):
        self.data_folder = "data"
        os.makedirs(self.data_folder, exist_ok=True)
        self.local_info_file = os.path.join(self.data_folder, "local_info.json")
        self.local_folder = self._load_local_folder()

    def _load_local_folder(self) -> str:
        if os.path.exists(self.local_info_file):
            with open(self.local_info_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("local_folder", "")
        return ""

    def save_local_folder(self, folder_path: str):
        with open(self.local_info_file, "w", encoding="utf-8") as f:
            json.dump({"local_folder": folder_path}, f)
        self.local_folder = folder_path

    def scan_markdown_files(self) -> List[str]:
        if not self.local_folder:
            return []
        markdown_files = []
        for root, _, files in os.walk(self.local_folder):
            for file in files:
                if file.endswith(".md"):
                    markdown_files.append(os.path.join(root, file))
        return markdown_files

    def get_embedding(self, text: str) -> List[float]:
        try:
            response = ollama.embeddings(model='nomic-embed-text', prompt=text)
            return response['embedding']
        except Exception as e:
            print(f"Embedding error: {str(e)}")
            return []

    def find_relevant_markdown_content(self, user_input: str) -> List[Dict]:
        relevant_content = []
        user_embedding = self.get_embedding(user_input)
        if not user_embedding:
            return relevant_content

        markdown_files = self.scan_markdown_files()
        for file_path in markdown_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                embedding = self.get_embedding(content)
                if not embedding:
                    continue
                try:
                    similarity = cosine_similarity([user_embedding], [embedding])[0][0]
                except ValueError:
                    continue
                if similarity > 0.55:
                    relevant_content.append({
                        "file_path": file_path,
                        "content": content,
                        "similarity": similarity
                    })
        return sorted(relevant_content, key=lambda x: x["similarity"], reverse=True)[:3]