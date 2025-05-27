import os
import json
from datetime import datetime
import ollama
from file_handler import FileHandler
from web_search import WebSearchHandler
from memory_handler import MemoryHandler

class ChatLogic:
    def __init__(self):
        self.current_conversation = []
        self._init_conversation()
        self.file_handler = FileHandler()
        self.web_search_handler = WebSearchHandler()
        self.memory_handler = MemoryHandler()
        self.file_mode_enabled = False

    def _init_conversation(self):
        self.current_conversation = []

    def generate_system_prompt(self):
        status = []
        if self.file_mode_enabled:
            status.append("работа с локальными файлами: ВКЛЮЧЕНА")
        else:
            status.append("работа с локальными файлами: ВЫКЛЮЧЕНА")
        
        if self.web_search_handler.enabled:
            status.append("веб-поиск: ВКЛЮЧЕН")
        else:
            status.append("веб-поиск: ВЫКЛЮЧЕН")

        system_message = (
            "Ты ИИ по имени Ай. Поддерживай естественный диалог без повторных приветствий."
            "Используй русский язык и кириллицу. Отвечай как дружелюбный помощник, учитывая контекст текущего и предыдущих разговоров, но не повторяй предыдущие ответы."
            "Старайся быть креативным и учитывать последний запрос пользователя.\n\n"
            f"Текущий статус системных функций:\n- {status[0]}\n- {status[1]}\n\n"
            "Если пользователь просит воспользоваться отключённой функцией, вежливо сообщи ему, что она отключена. Если функция включена, используй её при необходимости.\n"
            "Если какая-либо информация о пользователе была найдена в определённом файле (за исключением файла chat_log.jsonl), обязательно указывай из какого файла была взята данная информация. Никогда не выдумывай файлы, основывайся только на реальных данных из контекста."
            "Никогда не выдумывай информацию, если поьзователь об этом не просит напрямую. Основывай свои ответы только на реальных данных."
        )
        return {"role": "system", "content": system_message}

    def get_embedding(self, text):
        try:
            response = ollama.embeddings(model='nomic-embed-text', prompt=text)
            return response['embedding']
        except Exception as e:
            print(f"Embedding error: {str(e)}")
            return []

    def find_relevant_context(self, user_input):
        try:
            memory_context = self.memory_handler.find_relevant_context(user_input, max_results=2)
            return [
                f"- Из итога беседы ({m['start_timestamp']} - {m['end_timestamp']}): '{m['summary']}'"
                for m in memory_context
            ]
        except Exception as e:
            print(f"Context error: {str(e)}")
            return []

    def send_message(self, user_input):
        try:
            if not user_input.strip():
                return None

            self.current_conversation.append({
                "role": "user",
                "content": user_input
            })

            max_context_length = 6
            if len(self.current_conversation) > max_context_length:
                self.current_conversation = self.current_conversation[-max_context_length:]

            messages = [self.generate_system_prompt()] + [
                msg.copy() for msg in self.current_conversation if msg.get("role") != "system"
            ]

            context = []
            if self.file_mode_enabled:
                markdown_context = self.file_handler.find_relevant_markdown_content(user_input)
                if markdown_context:
                    context.append("Контекст из файлов:\n" + "\n".join(
                        f"- Файл: '{m['file_path']}'\n  Контент: '{m['content']}'"
                        for m in markdown_context
                    ))

            chat_context = self.find_relevant_context(user_input)
            if chat_context:
                context.append("Контекст из истории:\n" + "\n".join(chat_context))

            if self.web_search_handler.enabled:
                search_results = self.web_search_handler.perform_search(user_input)
                if self.web_search_handler.last_search_failed:
                    context.append("Внимание: веб-поиск недоступен. Ответ может быть неполным.")
                elif not search_results:
                    context.append("Веб-поиск не дал результатов. Ответ будет дан без дополнительной информации из интернета.")
                else:
                    context.append("Результаты веб-поиска:\n" + "\n".join(
                        f"- {res['title']} ({res['url']}): {res['content']}"
                        for res in search_results
                    ))

            if context:
                messages.insert(1, {"role": "system", "content": "\n".join(context)})

            response = ollama.chat(
                model="llama3",
                messages=messages,
                options={"temperature": 0.8}
            )
            ai_reply = response['message']['content']

            self.current_conversation.append({
                "role": "assistant",
                "content": ai_reply
            })

            self.memory_handler.add_message(user_input, ai_reply)
            
            return ai_reply
        except Exception as e:
            print(f"Processing error: {str(e)}")
            return "Извините, произошла ошибка. Попробуйте ещё раз."

    def toggle_file_mode(self, enabled: bool):
        self.file_mode_enabled = enabled
        if enabled and not self.file_handler.local_folder:
            return "Пожалуйста, укажите путь к локальной папке с markdown файлами."
        return None

    def finalize(self):
        self.memory_handler.finalize()
