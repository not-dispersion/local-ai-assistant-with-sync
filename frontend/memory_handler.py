import os
import json
from datetime import datetime
import ollama
from typing import List, Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity

class MemoryHandler:
    def __init__(self):
        self.data_folder = "data"
        os.makedirs(self.data_folder, exist_ok=True)
        self.summary_log_file = os.path.join(self.data_folder, "chat_summary.jsonl")
        self.embeddings_file = os.path.join(self.data_folder, "chat_embeddings.jsonl")
        self.summary_interval = 4
        self.summary_max_length = 500
        self.pending_messages = []
        self._ensure_log_files()
    
    def _ensure_log_files(self):
        for file_path in [self.summary_log_file, self.embeddings_file]:
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    pass
    
    def add_message(self, user_message: str, ai_reply: str):
        self.pending_messages.append({
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "ai_reply": ai_reply
        })
        
        if len(self.pending_messages) >= self.summary_interval:
            self.create_and_save_summary()
    
    def force_summary(self) -> bool:
        if self.pending_messages:
            return self.create_and_save_summary()
        return True
    
    def create_and_save_summary(self) -> bool:
        if not self.pending_messages:
            return False
            
        try:
            first_timestamp = self.pending_messages[0]["timestamp"]
            last_timestamp = self.pending_messages[-1]["timestamp"]
            
            conversation_text = "\n".join(
                f"User: {msg['user_message']}\nAi: {msg['ai_reply']}"
                for msg in self.pending_messages
            )
            
            summary = self._generate_summary(conversation_text)
            if len(summary) > self.summary_max_length:
                summary = summary[:self.summary_max_length-3] + "..."
            
            summary_embedding = self.get_embedding(summary)
            
            summary_entry = {
                "start_timestamp": first_timestamp,
                "end_timestamp": last_timestamp,
                "summary": summary
            }
            
            embedding_entry = {
                "start_timestamp": first_timestamp,
                "end_timestamp": last_timestamp,
                "embedding": summary_embedding
            }
            
            with open(self.summary_log_file, "a", encoding="utf-8") as file:
                file.write(json.dumps(summary_entry, ensure_ascii=False) + "\n")
                
            with open(self.embeddings_file, "a", encoding="utf-8") as file:
                file.write(json.dumps(embedding_entry, ensure_ascii=False) + "\n")
            
            self.pending_messages = []
            return True
            
        except Exception as e:
            print(f"Error creating summary: {str(e)}")
            return False
    
    def get_embedding(self, text: str) -> List[float]:
        try:
            response = ollama.embeddings(model='nomic-embed-text', prompt=text)
            return response['embedding']
        except Exception as e:
            print(f"Embedding error: {str(e)}")
            return []
    
    def _generate_summary(self, conversation_text: str) -> str:
        try:
            prompt = f"""Create a concise summary in Russian of the following conversation between user and AI.
Highlight key user information, interests, and important topics.
Summary should be no more than {self.summary_max_length} characters.

Conversation:
{conversation_text}

Summary:"""
            
            response = ollama.generate(
                model="llama3",
                prompt=prompt,
                options={"temperature": 0.5}
            )
            return response['response'].strip()
        except Exception as e:
            print(f"Summary generation error: {str(e)}")
            return f"Summary error: {str(e)}"
    
    def find_relevant_context(self, user_input: str, max_results: int = 2) -> List[Dict]:
        relevant_context = []
        user_embedding = self.get_embedding(user_input)
        if not user_embedding:
            return relevant_context
            
        summaries = self.load_summaries_and_embeddings()
        
        for summary in summaries:
            embedding = summary.get("embedding", [])
            if not embedding:
                continue
                
            try:
                similarity = cosine_similarity([user_embedding], [embedding])[0][0]
                if similarity > 0.7:
                    relevant_context.append({
                        "summary": summary.get("summary", ""),
                        "similarity": similarity,
                        "start_timestamp": summary.get("start_timestamp", ""),
                        "end_timestamp": summary.get("end_timestamp", "")
                    })
            except ValueError:
                continue
        
        return sorted(relevant_context, key=lambda x: x["similarity"], reverse=True)[:max_results]
    
    def load_summaries_and_embeddings(self) -> List[Dict]:
        summaries = {}
        embeddings = {}
        
        try:
            with open(self.summary_log_file, "r", encoding="utf-8") as file:
                for line in file:
                    if line.strip():
                        entry = json.loads(line)
                        key = f"{entry.get('start_timestamp')}_{entry.get('end_timestamp')}"
                        summaries[key] = entry
        except Exception as e:
            print(f"Error loading summaries: {str(e)}")
        
        try:
            with open(self.embeddings_file, "r", encoding="utf-8") as file:
                for line in file:
                    if line.strip():
                        entry = json.loads(line)
                        key = f"{entry.get('start_timestamp')}_{entry.get('end_timestamp')}"
                        embeddings[key] = entry.get("embedding", [])
        except Exception as e:
            print(f"Error loading embeddings: {str(e)}")
        
        result = []
        for key, summary in summaries.items():
            result.append({
                "summary": summary.get("summary", ""),
                "start_timestamp": summary.get("start_timestamp", ""),
                "end_timestamp": summary.get("end_timestamp", ""),
                "embedding": embeddings.get(key, [])
            })
        
        return result
    
    def finalize(self):
        if self.pending_messages:
            self.create_and_save_summary()