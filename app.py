from flask import Flask, request, abort
import os
import requests
import subprocess
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

list_last_actions_head_sha = []
bot_telegram_token = os.getenv('BOT_TELEGRAM_TOKEN', '')
id_telegram_for_log = os.getenv('ID_TELEGRAM_FOR_LOG', '')
port = os.getenv('PORT')
list_branches = ['main', 'master'] # Leave it blank for everyone to come up 
list_repo_push = ['repo1', 'repo2'] # Leave it blank for everyone to come up
list_repo_check_run = ['repo3', 'repo4'] # Leave it blank for everyone to come up

docker_compose_path = f'./docker-compose.yml'

def send_log(message):
    if not bot_telegram_token or not id_telegram_for_log:
        print(message)
        return
    formatted_message = message.replace('_', '\\_')
    url = f'https://api.telegram.org/bot{bot_telegram_token}/sendMessage'
    params = {'chat_id': id_telegram_for_log, 'text': formatted_message, 'parse_mode': 'MarkdownV2'}
    r = requests.get(url, params=params)
    return r.json()
    

send_log(f'🚀 *Webhook server started* \n running on port {port}')


def get_container_id(name):
    result = subprocess.run(['docker', 'ps', '-a', '--format', '{{.ID}} {{.Names}}'],
                            capture_output=True, text=True)
    for line in result.stdout.strip().split('\n'):
        container_id, container_name = line.split(' ', 1)
        if name in container_name:
            return container_id
    return None

def valid_head_sha(head_sha, service_name):
    if not head_sha or head_sha in list_last_actions_head_sha:
        return False
    list_last_actions_head_sha.append(head_sha)
    if len(list_last_actions_head_sha) > 5:
        list_last_actions_head_sha.pop(0)
    send_log(f"🔗 *New commit for {service_name}:* ```{head_sha}```")
    return True

 
def chack_docker_compose_file(service_name, docker_compose_path):
    if not os.path.exists(docker_compose_path):
        send_log(f"⚠️ *No docker\-compose file found for {service_name}*")
        abort(400, 'Docker-compose file not found')
    with open(docker_compose_path, 'r') as file:
        for line in file:
            if service_name in line:
                return True
        send_log(f"⚠️ *No service found in docker\-compose file for {service_name}*")
        return False


def update_docker_compose(service_name, docker_compose_path):
        try:
            subprocess.run(['git', '-C', service_name, 'pull'], check=True, text=True, capture_output=True )
            send_log(f"🔄 *Successfully pulled {service_name}*")
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.strip()
            send_log(f"⚠️ *Failed to git pull {service_name}:* \n```{error_message}```")
            return abort(500, f'Failed to git pull {service_name}: {error_message}')
        
        try:
            subprocess.run(['docker-compose', '-f', docker_compose_path, 'build', service_name], check=True)
            send_log(f"🔨 *Successfully built {service_name}*")
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.strip() 
            send_log(f"⚠️ *Failed to build service {service_name}:* \n```{error_message}```")
            abort(500, f'Failed to build service {service_name}: {error_message}')
            
        manage_docker_container(service_name)
        
        try:
            subprocess.run(['docker-compose', '-f', docker_compose_path, 'up', '-d', service_name], check=True, capture_output=True, text=True)
            send_log(f"🚀 *Successfully updated and scaled {service_name}*")
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.strip()  
            send_log(f"⚠️ *Failed to update service {service_name}:* \n```{error_message}```")
            abort(500, f'Failed to update service {service_name}: {error_message}')
            
    
def manage_docker_container(service_name):
    id_container = get_container_id(service_name)
    if id_container:
        subprocess.run(['docker', 'stop', id_container], check=True)
        send_log(f"⏹️ *Successfully stopped {service_name}*")
        subprocess.run(['docker', 'rm', id_container], check=True)
        send_log(f"🗑️ *Successfully removed {service_name}*")
        
def health_check_event(data):
    service_name = data['repository']['name']
    if len(list_repo_check_run) != 0 and service_name not in list_repo_check_run:
        send_log(f"⚠️ *Repository {service_name} not in list of repositories to check run*")
        return 'Webhook received and ignored', 200
    else:
        action = data.get('action', 'undefined')
        head_sha = data.get('check_run', {}).get('head_sha')
        service_name = data['repository']['name']
        head_branch = data['repository']['default_branch']    
        if len(list_repo_push) != 0 and head_branch not in list_branches:
            send_log(f"⚠️ *Branch {head_branch} not in list of branches*")
            return 'Webhook received and ignored', 200
        if chack_docker_compose_file(service_name, docker_compose_path):
            if action == 'completed':
                if valid_head_sha(head_sha, service_name):
                    re = update_docker_compose(service_name, docker_compose_path)
                    if re: return re
                return 'Webhook received and processed', 200
            return 'Webhook received and processed', 200
        return 'Webhook received and ignored', 200
        
def push_event(data):
    service_name = data['repository']['name']
    if len(list_repo_push) != 0 and service_name not in list_repo_push:
        send_log(f"⚠️ *Repository {service_name} not in list of repositories*")
        return 'Webhook received and ignored', 200
    else:
        head_branch =data['repository']['default_branch']
        if len(list_repo_push) != 0 and head_branch not in list_branches:
            send_log(f"⚠️ *Branch {head_branch} not in list of branches*")
            return 'Webhook received and ignored', 200
        if chack_docker_compose_file(service_name, docker_compose_path):
            if valid_head_sha(data['after'], service_name):
                update_docker_compose(service_name, docker_compose_path)
            return 'Webhook received and processed', 200
        return 'Webhook received and ignored', 200
        
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json()
    git_event = request.headers.get('X-GitHub-Event')
    if git_event == 'ping':
        send_log(f"🏓 *Ping event received*")
        return 'Webhook received and ignored', 200
    if git_event == 'push':
        return push_event(data)
    if git_event == 'check_run':
        return health_check_event(data)
    else:
        return 'Webhook received and ignored', 200        

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=port)
