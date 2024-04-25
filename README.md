
# How to use the project

1. clone the project from github

```
git clone https://github.com/ZviCode/Github_Hook_Deployer.git
```

2. change directory to the project directory
```
cd Github_Hook_Deployer
```

3. install the requirements using pip
```
pip install -r requirements.txt
```


4. set .env file with the following variables
* ```TELEGRAM_TOKEN=your_telegram_token```
* ```ID_TELEGRAM_FOR_LOG=your_telegram_id```
* ```PORT=your_port```

(If you do not add the telegram values, the logs will be printed to the terminal)


5. run the project using python
```
python app.py
```

6. create a webhook on github that points to the server where the project is running
* ```http://your_server_ip:your_port```

7. push code to the repository and see the webhook in action

8. check the logs in the telegram bot

9. enjoy the webhook



# It is very important!
I set the variables above either on or off, to know what to track on GitHub

check_run = True # if you want to check when the script github actions
push = True # If you want to check the push status


This is the folder tree that needs to be in your project for it to work
___________
main :
- app.py
- docker-compose.yml

- - project
- - project2


#Errors:

If you get an error like this every time,
"detected dubious ownership in repository at"
Consider running this script on a user who owns the git folder

It helped me
https://stackoverflow.com/a/73018171/18590647

If you have such an error message
"could not read Username for 'https://github.com': No such device or address"
It helped me
https://stackoverflow.com/a/71984173/18590647
