# FiveM-Server-Crawler
## This tool will crawl through your FiveM Resources Directory and create datasets based on using code as an answer that an LLM will synthetically generate questions for. These questions can be answered by another LLM or yourself to classify the results.

To use this please make sure you have Ollama installed from https://ollama.com
Also make sure your GPU can handle the model you are installing. For tasks like this on Consumer grade GPU's I recommend sticking with 1-3b Models,
If you have a 4090-5090 feel free to up this to around 7b.

Other than that, you need python on your system, I have python 3.11.9 for lots of AI applications that I run, so this is a safe bet.
Once Python and Ollama are both installed you want to add the crawl.py to your FiveM Resources folder and open a terminal windows from that folder (go to the address bar in the folder and type cmd, then hit enter)

In this command prompt window (which should display the name of your resources directory type in "python crawl.py" this will start the application.
You will see it gather information, ask questions and return lines.

The rest of the files are just tests and prep for model merging, which I recommend you do with RAG (feed the responses into a database the model can read from). This isn't training or fine-tuning. 
Merging takes time and GPU, RAG is smarter, add search to your data and it becomes even smarter. 

Be sure to join the AJTheDev discord for more cool FiveM Related projects:

https://discord.gg/d39aaZXAjh

I fix the bugs other devs gaslight you about.
AI tools, FiveM systems, automation pipelines.
Build it, break it, resurrect it: 👉 https://AJThe.Dev
