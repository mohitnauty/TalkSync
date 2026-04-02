# TalkSync
Real Time Voice Translation From English to Hindi, Punjabi etc.

#### Installation ####

## Clone repo ##
Open Terminal in directory where you want to setup this project

**git clone https://github.com/mohitnauty/TalkSync.git**

**cd TalkSync**

**Open Project in VS Code or in Any Editor, Open Editor Terminal**

## RUN Commands in project root directory.
1. python -m venv venv
2. venv\Scripts\activate
3. pip install -r requirements.txt (Make sure there is no error in terminal while installing packages or modules)
4. uvicorn app.main:app --reload --port 8000 (From root directory)
5. Open Chrome Browser and open URL **chrome://extensions**
6. Click on **LOAD UNPACKED**
7. Select extension folder from the project
8. Then Start Google Meet and after starting meeting you will see a popup window for translation of **TalkSync**.
9. Connect, Join and Click on Captur Google Audio (Always Toggle ON use tab audio with screen share)
