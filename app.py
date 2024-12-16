from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import requests
import os
import json
import time




IDS_FILE = os.getenv('IDS_FILE', 'ids.json')  
IDS_FILE2 = os.getenv('IDS_FILE2', 'ids2.json')  
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
CONTA_PRINCIPAL = os.getenv('CONTA_PRINCIPAL')
ROYAL_X = os.getenv('ROYAL_X')
EMPREENDEDOR_DO_FUTURO = os.getenv('EMPREENDEDOR_DO_FUTURO')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

created_media_records = []


def load_carrocel_ids():
    if os.path.exists(IDS_FILE):
        with open(IDS_FILE, "r") as file:
            return json.load(file)
    return []

def save_carrocel_ids(ids):
   
    with open(IDS_FILE, "w") as file:
        json.dump(ids, file)
        
def clear_carrocel_ids():
    
    if os.path.exists(IDS_FILE):
        os.remove(IDS_FILE)

##########################################################

def save_container_ids(ids):
   
    with open(IDS_FILE2, "w") as file:
        json.dump(ids, file)
        
def load_container_ids():
    if os.path.exists(IDS_FILE2):
        with open(IDS_FILE2, "r") as file:
            return json.load(file)
    return [] 
   
def clear_container_ids():
    
    if os.path.exists(IDS_FILE2):
        os.remove(IDS_FILE2)

#############################################################



def retry_request(url, data, max_retries=3, delay=2):
   
    for attempt in range(max_retries):
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response
        app.logger.warning(f"Tentativa {attempt + 1} falhou: {response.text}")
        time.sleep(delay)
    return response

def get_account_id(account_name):
    
    return {
        'Principal': CONTA_PRINCIPAL,
        'Royal X': ROYAL_X,
        'Empreendedor Do Futuro': EMPREENDEDOR_DO_FUTURO
    }.get(account_name)
    
def get_account_name(account_id):
   
    return {
        '17841401531671783': 'Principal',
        '17841463963815604': 'Royal X',
        '17841470729686161': 'Empreendedor Do Futuro'
    }.get(account_id)
    
# Routes





@app.route('/', methods=['GET', 'POST'])
def create_media():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            try:
                # Form data
                media_type = request.form['media_type']
                media_url = request.form['media_url']
                caption = request.form['caption']
                hashtags = request.form['hashtags']
                description = request.form['description']
                conta = request.form['conta']

                hide_likes = request.form.get('hide_likes') == 'on'
                hide_comments = request.form.get('hide_comments') == 'on'
                full_caption = f"{caption} {hashtags}"

                # Request parameters
                media_params = {
                    'access_token': ACCESS_TOKEN,
                    'caption': full_caption,
                    'hide_likes': hide_likes,
                    'hide_comments': hide_comments
                }
                
                conta_id = get_account_id(conta)
                
                if media_type == 'image':
                    media_params['image_url'] = media_url
                elif media_type == 'video':
                    media_params['video_url'] = media_url
                    media_params['media_type'] = 'REELS'

                create_url = f'https://graph.facebook.com/v21.0/{conta_id}/media'
                response = requests.post(create_url, params=media_params)

                if response.status_code == 200:
                    creation_id = response.json().get('id')
                    created_media_records.append({
                        'id': creation_id,
                        'conta': conta,
                        'type': media_type,
                        'caption': caption,
                        'description': description,
                        'hide_likes': hide_likes,
                        'hide_comments': hide_comments
                    })
                    flash(f'Mídia criada com sucesso! ID: {creation_id}', 'success')
                else:
                    flash(f'Erro ao criar a mídia: {response.json()}', 'danger')
            except Exception as e:
                flash(f'Erro: {str(e)}', 'danger')

        return redirect(url_for('create_media'))

    return render_template('create_media.html', created_media_records=created_media_records)


@app.route('/publish-media/<media_id>/<conta>', methods=['POST'])
def publish_media(media_id, conta):
    acount_id = get_account_id(conta)
    if not acount_id:
        flash("Conta inválida.", "danger")
        return redirect(url_for('create_media'))

    publish_url = f'https://graph.facebook.com/v21.0/{acount_id}/media_publish'
    response = requests.post(publish_url, params={
        'creation_id': media_id,
        'access_token': ACCESS_TOKEN
    })

    if response.status_code == 200:
        flash(f'Publicadas com sucesso!', 'success')
    else:
        flash(f'Erro ao publicar mídia {media_id}: {response.json()}', 'danger')

    return redirect(url_for('create_media'))


@app.route('/publish-all', methods=['POST'])
def publish_all_media():
    errors = []
    for media in created_media_records:
        try:
            publish_media(media['id'], media['conta'])
        except Exception as e:
            errors.append(f"Erro ao publicar {media['id']}: {str(e)}")

    if errors:
        for error in errors:
            flash(error, 'danger')
    else:
        flash("Todas as mídias foram publicadas com sucesso!", "success")
    return redirect(url_for('create_media'))


@app.route('/delete-media/<media_id>', methods=['POST'])
def delete_media(media_id):
    global created_media_records
    created_media_records = [m for m in created_media_records if m['id'] != media_id]
    flash(f'Mídia {media_id} excluída com sucesso.', 'success')
    return redirect(url_for('create_media'))








@app.route('/carrocel', methods=['GET', 'POST'])
def carrocel():
    media_ids = load_carrocel_ids()
    container_ids = load_container_ids()
   
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == "create":
            try:
                media_ids = load_carrocel_ids()
                media_url = request.form['media_url']
                description = request.form.get('description', '')
                media_type = request.form.get('type', '')  # Agora será 'image' ou 'video'
                conta = request.form.get('conta', '')

                # Verifique se o tipo de mídia é válido
                if media_type not in ['image_url', 'video_url']:
                    flash("Tipo de mídia inválido.", "danger")
                    return redirect(url_for('carrocel'))

                # Validar a URL de mídia (verifique se não está vazia)
                if not media_url:
                    flash(f"URL da {media_type} não fornecida.", "danger")
                    return redirect(url_for('carrocel'))

                conta_id = get_account_id(conta)
                if not conta_id:
                    flash("Conta não reconhecida.", "danger")
                    return redirect(url_for('carrocel'))

                # URL para criar mídia
                create_url = f'https://graph.facebook.com/v21.0/{conta_id}/media'
               
                media_data = {}
                # Adiciona o tipo correto de mídia (image ou video)
                if media_type == 'image_url':
                    media_data = {
                    'access_token': ACCESS_TOKEN,
                    'is_carousel_item': 'true',
                    'description': description,
                    'image_url': media_url
                } 
                elif media_type == 'video_url':
                    media_data = {
                    'access_token': ACCESS_TOKEN,
                    'is_carousel_item': 'true',
                    'description': description,
                    'media_type': 'REELS',
                    'video_url': media_url
                }
                else:    
                    flash(f"Erro ao idetificar a midia")
                    

                # Enviar a requisição para a API
                response = requests.post(create_url, data=media_data)

                # Verifique o resultado da requisição
                if response.status_code == 200:
                    media_ids.append({
                        'id': response.json().get('id'),
                        'conta': conta,
                        'description': description,
                        'type': media_type
                    })
                    save_carrocel_ids(media_ids)

                    flash(f"Mídia de {media_type} adicionada ao carrossel com sucesso!", "success")
                else:
                    # Se a resposta não for 200, exibe o erro detalhado
                    flash(f"Erro ao adicionar mídia: {response.text}", "danger")

                return redirect(url_for('carrocel'))
            except Exception as e:
                flash(f'Erro: {str(e)}', 'danger')
                
    return render_template('carrocel.html', media_ids=container_ids, container_ids=container_ids)




@app.route('/carrocel/deletar_lista', methods=['POST'])
def clear_all_ids():
    clear_carrocel_ids()
    clear_container_ids()
    flash("IDs limpos com sucesso!", "success")
    return redirect(url_for('carrocel'))

@app.route('/carrocel/criar_container', methods=['POST'])
def criar_container():
    action2 = request.form.get('action2')
    
    if action2 == "create2":
        # Carregar dados existentes
        media_ids = load_carrocel_ids()
        container_ids = load_container_ids()
        
        # Dados do formulário
        conta = request.form.get('conta')
        description = request.form.get('description')
        caption = request.form['caption']
        hashtags = request.form['hashtags']
        
        # Validar a conta
        conta_id = get_account_id(conta)
        if not conta_id:
            flash("Conta inválida.", "danger")
            return redirect(url_for('carrocel'))

        # Filtrar mídias associadas à conta
        filtered_media = [m['id'] for m in media_ids if m['conta'] == conta]
       
        
        """ filtered_container = [m['id'] for m in container_ids if m['conta'] == conta]
        if not filtered_container:
            flash("Nenhum container foi adicionado para esta conta.", "danger")
            return redirect(url_for('carrocel')) """

        # Criar o container do carrossel
        container_url = f'https://graph.facebook.com/v21.0/{conta_id}/media'
        container_data = {
            'access_token': ACCESS_TOKEN,
            'caption': f"{caption} {hashtags}",
            'media_type': 'CAROUSEL',
            'children': ",".join(filtered_media)
        }
        
        container_response = retry_request(container_url, container_data)
        
        if container_response.status_code == 200:
            # Obter ID do container e salvar
            container_id = container_response.json().get('id')
            if container_id:
                container_ids.append({
                    'id': container_id,
                    'conta': conta,
                    'description': description
                })
                save_container_ids(container_ids)
                flash("Carrossel criado com sucesso!", "success")
                
                # Limpar mídias após a criação do container
                clear_carrocel_ids()
            else:
                flash("Erro ao obter o ID do container do carrossel.", "danger")
                return redirect(url_for('carrocel'))
        else:
            flash(f"Erro ao criar container do carrossel: {container_response.text}", "danger")
            return redirect(url_for('carrocel'))

        # Renderizar template com os registros atualizados
        return render_template('carrocel.html', container_ids=container_ids)
    else:
        flash("Ação inválida.", "danger")
        return redirect(url_for('carrocel'))



@app.route('/carrocel/publicar_container', methods=['POST'])
def publicar_container():
    action3 = request.form.get('action3')
    
    if action3 == "publish":
        # Carregar dados existentes
        container_ids = load_container_ids()

        # Dados do formulário
        conta = request.form.get('conta')
        
        # Validar a conta
        conta_id = get_account_id(conta)
        if not conta_id:
            flash("Conta inválida.", "danger")
            return redirect(url_for('carrocel'))

        # Encontrar o container a ser publicado
        container_id = None
        for container in container_ids:
            if container['conta'] == conta:
                container_id = container['id']
                break
        
        if not container_id:
            flash("Nenhum container encontrado para esta conta.", "danger")
            return redirect(url_for('carrocel'))
        
        # Publicar o carrossel
        publish_url = f'https://graph.facebook.com/v21.0/{conta_id}/media_publish'
        publish_data = {
            'access_token': ACCESS_TOKEN,
            'creation_id': container_id
        }

        publish_response = retry_request(publish_url, publish_data)

        if publish_response.status_code == 200:
            flash("Carrossel publicado com sucesso!", "success")
            
            # Excluir o container publicado da lista de containers
            container_ids = [container for container in container_ids if container['id'] != container_id]
            save_container_ids(container_ids)  # Atualizar os containers salvos

            flash("Container excluído após publicação.", "info")
        else:
            flash(f"Erro ao publicar o carrossel: {publish_response.text}", "danger")

        # Renderizar template com os registros atualizados
        return render_template('carrocel.html', container_ids=container_ids)

    else:
        flash("Ação inválida.", "danger")
        return redirect(url_for('carrocel'))


@app.route('/carrocel/excluir_container', methods=['POST'])
def excluir_container():
    action3 = request.form.get('action3')
    
    if action3 == "delete":
        # Carregar dados existentes
        container_ids = load_container_ids()

        # Dados do formulário
        container_id = request.form.get('container_id')
        conta = request.form.get('conta')
        
        # Validar a conta
        conta_id = get_account_id(conta)
        if not conta_id:
            flash("Conta inválida.", "danger")
            return redirect(url_for('carrocel'))

        # Filtrar o container para remover
        container_ids = [container for container in container_ids if container['id'] != container_id]
        save_container_ids(container_ids)

        flash("Container excluído com sucesso!", "success")

        # Renderizar template com os registros atualizados
        return redirect(url_for('carrocel'))
    
    else:
        flash("Ação inválida.", "danger")
        return redirect(url_for('carrocel'))


@app.route('/carrocel/publicar_todos', methods=['POST'])
def publicar_todos_carroceis():
    try:
        # Carregar os IDs dos containers existentes
        container_ids = load_container_ids()
        
        # Verificar se há containers para publicar
        if not container_ids:
            flash("Nenhum carrossel criado para publicação.", "danger")
            return redirect(url_for('carrocel'))
        
        # Percorrer todos os carrosséis e publicar um por um
        for container in container_ids:
            conta_id = get_account_id(container['conta'])
            
            if not conta_id:
                flash(f"Conta {container['conta']} inválida. Não foi possível publicar o carrossel.", "danger")
                continue

            # Publicar o carrossel usando o ID do container
            publish_url = f'https://graph.facebook.com/v21.0/{conta_id}/media_publish'
            publish_data = {
                'access_token': ACCESS_TOKEN,
                'creation_id': container['id']  # ID do container
            }

            # Enviar requisição para publicar o carrossel
            publish_response = retry_request(publish_url, publish_data)
            
            if publish_response.status_code == 200:
                clear_carrocel_ids()
                clear_container_ids()
                flash(f"Carrossel {container['id']} publicado com sucesso!", "success")
            else:
                flash(f"Erro ao publicar o carrossel {container['id']}: {publish_response.text}", "danger")
        
        # Renderizar a página de carrossel com mensagens
        return redirect(url_for('carrocel'))

    except Exception as e:
        flash(f"Ocorreu um erro ao tentar publicar os carrosséis: {str(e)}", "danger")
        return redirect(url_for('carrocel'))
# Main Function

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = '127.0.0.1' if debug_mode else '0.0.0.0'
    app.run(host=host, port=port, debug=debug_mode)
