## Description
This is a DEMO version of my local AI-assistant, that remembers every conversation with user. it is capable of working with Makrkdown files and Web. In this version, it is now possible to register a user profile and synchronise conversation history with the cloud.

## Warning!!
The program (including all the required libraries, llama3 7b and nomic-embed-text models pulled with Ollama) is going to take more than 7 GB of a disc space!! Python 3.10+ is required to run the program.

## How to run the code:
- Download, install and run the Ollama. Official website - https://ollama.com/
- Open terminal in a code editor you use and run the comands:
```
ollama pull llama3
```
Wait for ollama to pull and then run:
```
ollama pull nomic-embed-text
```
- Open the directory with project, create and activate virtual enviroment
(If you don't know how to do it, here is an instruction: https://docs.python.org/3/library/venv.html).
- Install necessary libraries from the **requirements.txt** file into the created virtual enviroment by running the comand:
```
pip install -r requirements.txt
```
Generate a secret key by running the following script and paste it to the **app.py** file:
```
import secrets
print(secrets.token_hex(32))
```
Run the **certificate_gen.py** to generate .pem files.
 
# You can now run the code by starting the cloud server with app.py and then running main.py
